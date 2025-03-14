# helper functions

import datetime
import io
import json
import logging
import os
import re
import time
from multiprocessing import Process

import grequests
import numpy as np
import pjsua2 as pj
import requests
import soundfile as sf
from minio import Minio
from redis import Redis

from config import AIEndpoints, Algorithm, CallbackAPIs, ObjectStorage, UserAgent
from custom_callbacks import Call
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


def run_am_asr_kws(data):
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
        return "", "", {}
    # run decoder algorithms in parallel
    urls = [
        AIEndpoints.asr_decoder_endpoint,
        AIEndpoints.amd_kws_endpoint,
    ]
    rs = (grequests.get(u, data=am_result, timeout=AIEndpoints.timeout) for u in urls)
    asr_response, kws_response = grequests.map(rs)
    asr_result = asr_response.text if asr_response.status_code == 200 else ""
    kws_result = kws_response.text if kws_response.status_code == 200 else "{}"

    logger.info(f"@run_am_asr_kws {asr_result = }")
    logger.info(f"@run_am_asr_kws {kws_result = }")
    return am_result, asr_result, kws_result


def lookahead_am_asr_kws_pipeline(data, call_id):
    # run am and asr
    am_result, asr_result, kws_result = run_am_asr_kws(data)
    # generate key for result
    redis_key_postfix = f"{call_id}_{time.time()}"
    am_redis_key = "am_" + redis_key_postfix
    asr_redis_key = "asr_" + redis_key_postfix
    kws_redis_key = "kws_" + redis_key_postfix
    # put result in redis
    redis = Redis(
        host=Algorithm.redis_host,
        port=Algorithm.redis_port,
        decode_responses=True,
    )
    redis.set(am_redis_key, am_result, ex=6000)
    redis.set(asr_redis_key, asr_result, ex=6000)
    redis.set(kws_redis_key, kws_result, ex=6000)


def spawn_background_am_asr_kws(data, call_id):
    logger = get_logger()
    logger.info("spawn am + asr background process...")
    p = Process(target=lookahead_am_asr_kws_pipeline, args=(data, call_id))
    p.start()
    return p


def recover_last_key_and_result(key_regex):
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


def recover_am_asr_kws(call_id):
    last_am_key, last_am_result = recover_last_key_and_result(f"am_{call_id}_*")
    last_asr_key, last_asr_result = recover_last_key_and_result(f"asr_{call_id}_*")
    last_kws_key, last_kws_result = recover_last_key_and_result(f"kws_{call_id}_*")
    if last_am_key is None:
        return None, "", ""
    return last_am_result, last_asr_result, last_kws_result


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
            now_datetime.year,
            now_datetime.month,
            now_datetime.day,
        )
        amd_record = AMDRecord(
            metadata_dict["call_id"],
            metadata_dict["dialed_number"],
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
            logger.warning(f"non-200 status code for {url}")
            response = None
    except requests.exceptions.Timeout:
        logger.warning(f"Latency for {url} is high!")
        response = None
    if response is None:
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
