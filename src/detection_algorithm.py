# answering machine detection algorithm

import json
import time

import numpy as np
import pjsua2 as pj
import soundfile as sf

from audio_matching import AudioMatching
from config import Algorithm
from custom_callbacks import Call
from sad.sad_model import SAD
from utils import (
    convert_np_array_to_wav_file_bytes,
    delete_pj_obj_safely,
    get_amd_record,
    get_logger,
    get_number,
    parse_new_frames,
    recover_am_asr_kws,
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

    # audio recorder
    wav_writer = pj.AudioMediaRecorder()
    wav_filename = call_id + ".wav"
    wav_writer.createRecorder(wav_filename)
    time.sleep(0.1)

    # capture audio media
    aud_med = call.getAudioMedia(0)
    aud_med.startTransmit(wav_writer)

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
    zero_buffer = np.zeros(Algorithm.zero_padding, dtype=np.float32)
    t0 = time.time()
    audio_buffer = zero_buffer.copy()
    sad_result = []
    while time.time() - t0 < Algorithm.max_call_duration:
        appended_bytes = wav_file.read()
        if len(appended_bytes) == 0:
            time.sleep(0.01)
            continue
        new_buffer = parse_new_frames(appended_bytes, wav_info)
        audio_buffer = np.concatenate([audio_buffer, new_buffer])
        data = convert_np_array_to_wav_file_bytes(audio_buffer, fs)
        sad_result = sad.handle([data])[0]
        if len(sad_result):
            audio_buffer_duration = audio_buffer.shape[0] / fs
            tail_sil = audio_buffer_duration - sad_result[-1]["end"]
            if tail_sil > Algorithm.max_tail_sil:
                logger.info("tail silence detected")
                logger.info(f"{sad_result = }")
                break
            else:
                # rational sleep
                time.sleep(0.1)
                continue
        time.sleep(0.2)

    # create metadata dict
    metadata_dict = {
        "call_id": call_id,
        "dialed_number": dialed_number,
        "result": "",
        "duration": time.time() - t0,
        "sad_result": sad_result,
    }

    # check if SAD detects any speech signal
    t1 = time.time()
    if len(sad_result) == 0:
        logger.warning("No speech detected!")
        metadata_dict["result"] = "non-AMD"
        metadata_dict["asr_result"]
        return metadata_dict
    start_sample = int(sad_result[0]["start"] * fs)
    end_sample = int(sad_result[-1]["end"] * fs)
    audio_segment = audio_buffer[start_sample:end_sample]
    data = convert_np_array_to_wav_file_bytes(audio_segment, fs)

    # ASR (non blocking)
    process = spawn_background_am_asr_kws(data, call_id)

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
    while process.is_alive():
        time.sleep(0.01)
    am_result, asr_result, kws_result = recover_am_asr_kws(call_id)
    kws_result = json.loads(kws_result)
    logger.info(f"{asr_result = }")
    metadata_dict["asr_result"] = asr_result
    logger.info(f"{kws_result = }")
    metadata_dict["kws_result"] = kws_result

    # asr string matching
    asr_repeat = old_asr_result == asr_result
    logger.info(f"{asr_repeat = }")

    # keyword spotting
    keywords_detected = len(kws_result) > 0
    logger.info(f"{keywords_detected = }")

    # audio pattern matching
    audio_matching = AudioMatching()
    matching_result = audio_matching.match_segments(audio_segment, old_wav_obj)
    logger.info(f"{matching_result = }")

    # TODO: search keywords in ASR result

    # ensemble of results
    if asr_repeat or keywords_detected or matching_result:
        metadata_dict["result"] = "AMD"
    else:
        metadata_dict["result"] = "non-AMD"
    metadata_dict["process_duration"] = time.time() - t1
    logger.warning(f"processing duration: {metadata_dict['process_duration']}")
    logger.info(f"{metadata_dict['result'] = }")

    # log and return
    logger.info(f"{metadata_dict = }")
    # delete pjsua objects
    wav_writer.stopTransmit()
    delete_pj_obj_safely(wav_writer)
    delete_pj_obj_safely(aud_med)
    logger.info("Return to UA")
    return metadata_dict
