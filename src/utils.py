# helper functions

import datetime
import io
import json
import logging
import os
import re
import time
from multiprocessing import Process

import numpy as np
import pjsua2 as pj
import requests
import soundfile as sf
from minio import Minio
from redis import Redis

from custom_callbacks import Call
from config import AIEndpoints, Algorithm, CallbackAPIs, ObjectStorage, UserAgent
from database import db_session
from models import AMDRecord
from sad.sad_model import SAD

_logger = None


def get_logger() -> logging.Logger:
    """Get logger."""
    global _logger
    if _logger is None:
        logging.basicConfig(
            format="AMD-LOG %(asctime)s\t%(levelname)s\t%(message)s",
            level=UserAgent.log_level,
        )
        _logger = logging.getLogger()
    return _logger


def get_number(remote_uri):
    pattern = re.compile(r"<sip:[+]*(\d+)@")
    match_pattern = pattern.search(remote_uri)
    try:
        return match_pattern.group(1)
    except AttributeError:
        return "NEW-PATTERN:" + remote_uri


def parse_new_frames(appended_bytes, info):
    data = np.frombuffer(appended_bytes, dtype=np.int16)
    data = data[:: info.channels]
    data = data / (2**15)
    return data.astype(np.float32)


def convert_np_array_to_wav_file_bytes(np_array, fs):
    in_memory_file = io.BytesIO()
    sf.write(in_memory_file, np_array, fs, format="WAV")
    in_memory_file.seek(0)
    return in_memory_file.read()


def run_am_asr(data):
    logger = get_logger()
    # run am model
    am_result = call_api_non_blocking(
        AIEndpoints.am_endpoint,
        data,
        "",
        AIEndpoints.timeout,
    )
    if am_result == "":
        logger.warning("check acoustic model...")
        return "", ""
    else:
        # run decoder algorithm
        asr_result = call_api_non_blocking(
            AIEndpoints.asr_decoder_endpoint,
            am_result,
            "",
            AIEndpoints.timeout,
        )
        logger.info(f"@run_am_asr {asr_result = }")
        return am_result, asr_result


def lookahead_am_asr_pipeline(data, call_id):
    # run am and asr
    am_result, asr_result = run_am_asr(data)
    # generate key for result
    redis_key_postfix = f"{call_id}_{time.time()}"
    am_redis_key = "am_" + redis_key_postfix
    asr_redis_key = "asr_" + redis_key_postfix
    # put result in redis
    redis = Redis(
        host=Algorithm.redis_host,
        port=Algorithm.redis_port,
        decode_responses=True,
    )
    redis.set(am_redis_key, am_result, ex=6000)
    redis.set(asr_redis_key, asr_result, ex=6000)


def spawn_background_am_asr(data, call_id):
    logger = get_logger()
    logger.info("spawn am + asr background process...")
    p = Process(target=lookahead_am_asr_pipeline, args=(data, call_id))
    p.start()
    return p


def recover_last_key(key_regex):
    redis = Redis(
        host=Algorithm.redis_host,
        port=Algorithm.redis_port,
        decode_responses=True,
    )
    keys = sorted(redis.keys(key_regex))
    try:
        key = keys[-1]
    except IndexError:
        key = None
    if key is None:
        return None, None
    else:
        return key, redis.get(key)


def recover_am_asr(call_id):
    logger = get_logger()
    last_am_key, last_am_result = recover_last_key(f"am_{call_id}_*")
    last_asr_key, last_asr_result = recover_last_key(f"asr_{call_id}_*")
    if last_am_key is None or last_asr_key is None:
        return None, "", ""
    am_insertion_time = float(last_am_key.split("_")[-1])
    asr_insertion_time = float(last_asr_key.split("_")[-1])
    if am_insertion_time != asr_insertion_time:
        logger.info("am and asr insertion time are different!")
        return None, "", ""
    return am_insertion_time, last_am_result, last_asr_result


def get_amd_record(dialed_number):
    logger = get_logger()
    try:
        amd_record = (
            db_session.query(AMDRecord)
            .filter_by(dialed_number=dialed_number)
            .order_by(AMDRecord.call_date.desc(), AMDRecord.call_time.desc())
            .first()
        )
        if amd_record is None:
            return None
        return amd_record
    except:
        logger.exception("Can not fetch AMD record from database.")
        return None


def detect_answering_machine(call: Call) -> None:
    """Detect answering machine."""
    logger = get_logger()
    call_info = call.getInfo()
    call_id = call_info.callIdString
    dialed_number = get_number(call_info.remoteUri)
    logger.info(f"Call ID: {call_id}")

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
    sad = None
    t0 = time.time()
    while time.time() - t0 < Algorithm.max_call_duration:
        if sad is None:
            sad = SAD()
        time.sleep(0.01)

    # process audio data
    appended_bytes = wav_file.read()
    audio_buffer = parse_new_frames(appended_bytes, wav_info)
    zero_buffer = np.zeros(Algorithm.zero_padding, dtype=np.float32)
    audio_buffer = np.concatenate((zero_buffer, audio_buffer, zero_buffer))
    data = convert_np_array_to_wav_file_bytes(audio_buffer, fs)
    sad_result = sad.handle([data])[0]

    # create metadata dict
    metadata_dict = {
        "call_id": call_id,
        "dialed_number": dialed_number,
        "result": "",
    }

    # check if SAD detects any speech signal
    if len(sad_result) == 0:
        logger.warning("No speech detected!")
        metadata_dict["result"] = "non-AMD"
        metadata_dict["asr_result"]
        metadata_dict["duration"] = time.time() - t0
        return metadata_dict
    start_sample = int(sad_result[0]["start"] * fs)
    end_sample = int(sad_result[-1]["end"] * fs)
    audio_segment = audio_buffer[start_sample:end_sample]
    data = convert_np_array_to_wav_file_bytes(audio_segment, fs)

    # ASR (non blocking)
    process = spawn_background_am_asr(data, call_id)

    # fetch history
    old_amd_record = get_amd_record(dialed_number)

    # retrieve ASR result
    while process.is_alive():
        time.sleep(0.01)
    am_insertion_time, am, asr_result = recover_am_asr(call_id)

    # asr string matching
    metadata_dict["asr_result"] = asr_result
    if old_amd_record and old_amd_record.asr_result == asr_result:
        metadata_dict["result"] = "AMD"
    else:
        metadata_dict["result"] = "non-AMD"

    # TODO: keyword spotting
    # TODO: audio pattern matching
    return metadata_dict


def store_wav(file_path):
    logger = get_logger()
    try:
        client = Minio(
            ObjectStorage.minio_url,
            access_key=ObjectStorage.minio_access_key,
            secret_key=ObjectStorage.minio_secret_key,
            secure=False,
        )
        client.fput_object(
            ObjectStorage.minio_wav_bucket_name,
            file_path,
            file_path,
        )
        os.remove(file_path)
    except:
        logger.exception("Can not store wav file in object storage.")


def store_metadata(metadata_dict):
    file_path = metadata_dict["call_id"] + ".json"
    logger = get_logger()
    try:
        client = Minio(
            ObjectStorage.minio_url,
            access_key=ObjectStorage.minio_access_key,
            secret_key=ObjectStorage.minio_secret_key,
            secure=False,
        )
        json_data = json.dumps(metadata_dict)
        json_data_len = len(json_data)
        json_data = io.BytesIO(json_data.encode())
        client.put_object(
            ObjectStorage.minio_metadata_bucket_name,
            file_path,
            json_data,
            json_data_len,
        )
    except:
        logger.exception("Can not store metadata in object storage.")
        with open(file_path, "w") as f:
            json.dump(metadata_dict, f, indent=4)


def add_call_log_to_database(metadata_dict):
    logger = get_logger()
    try:
        now_datetime = datetime.datetime.now()
        now_time = datetime.time(
            now_datetime.hour,
            now_datetime.minute,
            now_datetime.second,
            now_datetime.microsecond,
        )
        now_date = datetime.date(
            now_datetime.year, now_datetime.month, now_datetime.day
        )
        amd_record = AMDRecord(
            metadata_dict["dialed_number"],
            metadata_dict["call_id"],
            now_date,
            now_time,
            metadata_dict["result"],
            metadata_dict["duration"],
            metadata_dict["asr_result"],
        )
        db_session.add(amd_record)
        db_session.commit()
    except:
        logger.info("Cannot save metadata in database!")


def call_api_non_blocking(url, data, default, timeout):
    logger = get_logger()
    try:
        response = requests.get(url, data=data, timeout=timeout)
        if response.status_code != 200:
            response = None
    except requests.exceptions.Timeout:
        response = None
    if response is None:
        logger.warning(f"Latency for {url} is high!")
        return default
    if isinstance(default, str):
        return response.text
    else:
        return response.json()


def call_api():
    logger = get_logger()
    logger.info("Calling API")
    call_api_non_blocking(CallbackAPIs.address, None, "", 1.0)


def delete_pj_obj_safely(pj_obj):
    try:
        del pj_obj
    except pj.Error:
        pass
