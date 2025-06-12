# answering machine detection algorithm

import json
import time

import numpy as np
import pjsua2 as pj
import soundfile as sf

from audio_matching import AudioMatching
from config import Algorithm, KWSConfig
from custom_callbacks import Call

from streamsad import SAD
from utils import (
    aggregate_kws_results,
    convert_np_array_to_wav_file_bytes,
    get_amd_record,
    get_background_noise,
    get_sad_audio_buffer_duration,
    get_logger,
    get_number,
    parse_new_frames,
    recover_asr_kws_results,
    recover_keys_and_results,
    spawn_background_am_asr_kws,
)


def detect_answering_machine(call: Call) -> None:
    """Detect answering machine."""
    logger = get_logger()
    call_info = call.getInfo()
    call_id = call_info.callIdString
    logger.info(f"Call ID: {call_id}")
    dialed_number = get_number(call_info.remoteUri)
    logger.info(f"Dialed number: {dialed_number}")
    metadata_dict = {
        "call_id": call_id,
        "dialed_number": dialed_number,
        "asr_result": "",
        "kws_result": {},
        "result": "",
    }

    # audio recorder
    wav_writer = pj.AudioMediaRecorder()
    wav_filename = call_id + ".wav"
    wav_writer.createRecorder(wav_filename)
    time.sleep(0.1)

    # capture audio media
    aud_med = call.getAudioMedia(0)
    aud_med.startTransmit(wav_writer)

    # start playing background noise
    playback_path = get_background_noise()
    metadata_dict["playback"] = playback_path
    if playback_path:
        logger.info(f"{playback_path = }")
        playback_info = sf.info(playback_path)
        logger.info(f"playback time: {playback_info.duration}")
        player = pj.AudioMediaPlayer()
        player.createPlayer(playback_path, pj.PJMEDIA_FILE_NO_LOOP)
        player.startTransmit(aud_med)
    else:
        logger.info("No playback...")

    # wait till wav file is created
    wav_info = None
    while wav_info is None:
        try:
            wav_info = sf.info(wav_filename)
            # assume wav subtype is PCM_16 with sampling rate of 16 kHz
            wav_file = open(wav_filename, "rb")
            wav_file.read(44)
        except sf.LibsndfileError:
            time.sleep(0.01)
    fs = wav_info.samplerate

    # gather first few seconds of the call
    # Note: each packet appended every 100-120 ms (jitter absolutely possible!)
    sad = SAD()
    sad_results = []
    process_list = []
    break_while = False
    t0 = time.time()
    time.sleep(Algorithm.receiving_silent_segment_sleep)
    while time.time() - t0 < Algorithm.max_call_duration:
        # check process list for early AM detection
        logger.info(f"process list check...")
        for index, process in enumerate(process_list):
            logger.info(f"Process {process.pid} is alive: {process.is_alive()}")
            if not process.is_alive():
                _, kws_results = recover_keys_and_results(f"kws_{call_id}_{index}_*")
                kws_result = kws_results[0]
                kws_result = json.loads(kws_result)
                if len(kws_result) > 0:
                    logger.info(f"Early AM detection @KWS")
                    metadata_dict["reason"] = "early kws"
                    break_while = True
                    break
                _, asr_results = recover_keys_and_results(f"asr_{call_id}_{index}_*")
                asr_result = asr_results[0]
                kw_in_asr_result = any(
                    [kw in asr_result for kw in KWSConfig.am_keywords]
                )
                if kw_in_asr_result:
                    logger.info(f"Early AM detection @ASR")
                    metadata_dict["reason"] = "early asr"
                    break_while = True
                    break
        if break_while:
            break
        # read new segments
        appended_bytes = wav_file.read()
        if len(appended_bytes) == 0:
            logger.info("Pooling for audio data...")
            time.sleep(Algorithm.chunk_interval)
            continue
        new_buffer = parse_new_frames(appended_bytes, wav_info)
        sad_result = sad(new_buffer)
        sad_results.extend(sad_result)
        # calculate trailing silence
        audio_buffer_duration = get_sad_audio_buffer_duration(sad, fs)
        last_segment_end = sad_results[-1]["end"] if sad_results else 0.0
        tail_sil = audio_buffer_duration - last_segment_end
        if (
            len(sad_result) == 0
            and tail_sil > Algorithm.max_tail_sil
            and len(process_list) > 0
            and not sad.triggered
        ):
            logger.info("Silenced for a long time...")
            break
        if sad_result:
            logger.info(f"{tail_sil = }")
            # receiving segment
            logger.info(f"Silenced for a short time...")
            audio_segment = sad.get_audio(sad_result[0])
            data = convert_np_array_to_wav_file_bytes(audio_segment, fs)
            # spawn ASR and KWS processes
            segment_number = len(process_list)
            process = spawn_background_am_asr_kws(data, call_id, segment_number)
            process_list.append(process)
            # reset audio buffer
            time.sleep(Algorithm.receiving_silent_segment_sleep)
        elif len(process_list) == 0:
            logger.info("No activity detected yet! Going to a long sleep")
            time.sleep(Algorithm.receiving_silent_segment_sleep)

    # evacuate audio buffer in case the call is too long and the last segment is not detected via max_tail_sil
    if time.time() - t0 > Algorithm.max_call_duration and sad.triggered:
        sad_result = sad(np.zeros(16000))
        if sad_result:
            # audio_buffer = sad_result[0]["audio"]
            audio_buffer = sad.get_audio(sad_result[0])
            data = convert_np_array_to_wav_file_bytes(audio_buffer, fs)
            # spawn ASR and KWS processes
            segment_number = len(process_list)
            process = spawn_background_am_asr_kws(data, call_id, segment_number)
            process_list.append(process)

    # update metadata dict
    metadata_dict["sad_result"] = sad_results
    metadata_dict["duration"] = time.time() - t0
    logger.info(f"{sad_results = }")

    # fetch history
    old_amd_record = get_amd_record(dialed_number)
    try:
        old_asr_result = old_amd_record.asr_result
        logger.info(f"{old_asr_result = }")
        old_wav_obj = old_amd_record.call_id + ".wav"
        logger.info(f"{old_wav_obj = }")
    except Exception as e:
        logger.warning(f"{e = }")
        old_asr_result = ""
        old_wav_obj = ""

    # retrieve ASR result
    t1 = time.time()
    while any([process.is_alive() for process in process_list]):
        time.sleep(0.1)
        if time.time() - t1 > AIEndpoints.timeout:
            logger.info("ASR and KWS takes too long to finish...")
            metadata_dict["last_segment_retrieve"] = time.time() - t1
            break
    process_duration = time.time() - t1
    asr_segment_results, kws_segment_results = recover_asr_kws_results(call_id)
    asr_result = " ".join(asr_segment_results)
    kws_result = aggregate_kws_results(kws_segment_results)

    logger.info(f"{asr_result = }")
    metadata_dict["asr_result"] = asr_result
    logger.info(f"{kws_result = }")
    metadata_dict["kws_result"] = kws_result

    # asr string matching
    asr_repeat = (old_asr_result == asr_result) and (len(asr_result) > 0)
    logger.info(f"{asr_repeat = }")
    metadata_dict["asr_repeat"] = asr_repeat

    # keyword spotting
    keywords_detected = len(kws_result) > 0
    logger.info(f"{keywords_detected = }")
    metadata_dict["keywords_detected"] = keywords_detected

    # audio pattern matching
    audio_matching = AudioMatching()
    matching_result = audio_matching.match_segments(audio_segment, old_wav_obj)
    logger.info(f"{matching_result = }")
    metadata_dict["matching_result"] = matching_result

    # search keywords in ASR result
    kw_in_asr_result = any([keyword in asr_result for keyword in KWSConfig.am_keywords])
    logger.info(f"{kw_in_asr_result = }")
    metadata_dict["kw_in_asr_result"] = kw_in_asr_result

    # ensemble of results
    if asr_repeat or keywords_detected or matching_result or kw_in_asr_result:
        metadata_dict["result"] = "AMD"
    else:
        metadata_dict["result"] = "non-AMD"
    metadata_dict["process_duration"] = process_duration
    logger.warning(f"{process_duration = }")
    logger.info(f"{metadata_dict['result'] = }")

    # log and return
    logger.info(f"{metadata_dict = }")
    # delete pjsua objects
    if playback_path:
        player.stopTransmit(aud_med)
        del player
    aud_med.stopTransmit(wav_writer)
    logger.info("Return to UA")
    return metadata_dict
