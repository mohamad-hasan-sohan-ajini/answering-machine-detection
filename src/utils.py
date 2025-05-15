# helper functions

import datetime
import io
import json
import logging
import os
import re
import time
from collections import defaultdict
from multiprocessing import Process

import grequests
import numpy as np
import pjsua2 as pj
import requests
import soundfile as sf
import torch
import torchaudio
from minio import Minio
from redis import Redis
from sqlalchemy import text

from config import (
    AIEndpoints,
    Algorithm,
    CallbackAPIs,
    Database,
    KWSConfig,
    ObjectStorage,
    UserAgent,
)
from database import db_session
from models import AMDRecord
from wrapper import KWSDecoder

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
    kws_result = filter_kws_result(kws_result)

    logger.info(f"@run_am_asr_kws {asr_result = }")
    logger.info(f"@run_am_asr_kws {kws_result = }")
    return am_result, asr_result, kws_result


def lookahead_am_asr_kws_pipeline(data, call_id, segment_number):
    # run am and asr
    am_result, asr_result, kws_result = run_am_asr_kws(data)
    # generate key for result: [am|asr|kws] + call_id + segment_number + time
    redis_key_postfix = f"{call_id}_{segment_number}_{time.time()}"
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


def spawn_background_am_asr_kws(data, call_id, segment_number):
    logger = get_logger()
    logger.info("spawn am + asr background process...")
    p = Process(
        target=lookahead_am_asr_kws_pipeline,
        args=(data, call_id, segment_number),
    )
    p.start()
    return p


def recover_keys_and_results(key_regex):
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
        return [], []
    else:
        return keys, [redis.get(key) for key in keys]


def recover_asr_kws_results(call_id):
    asr_keys, asr_results = recover_keys_and_results(f"asr_{call_id}_*")
    _, kws_results = recover_keys_and_results(f"kws_{call_id}_*")
    if asr_keys:
        return asr_results, kws_results
    return [], []


def get_amd_record(dialed_number):
    logger = get_logger()
    try:
        db_session.execute(text(f"SET LOCAL statement_timeout TO {Database.timeout}"))
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


def retrieve_wav(obj_name):
    logger = get_logger()
    try:
        client = Minio(
            ObjectStorage.minio_url,
            access_key=ObjectStorage.minio_access_key,
            secret_key=ObjectStorage.minio_secret_key,
            secure=False,
        )
        response = client.get_object(ObjectStorage.minio_wav_bucket_name, obj_name)
        in_memory_wav_file = io.BytesIO(response.read())
        wav_array, fs = torchaudio.load(in_memory_wav_file)
    except:
        logger.exception("Can not retrieve wav file in object storage.")
        wav_array = torch.Tensor()
    return wav_array


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
    except Exception as e:
        logger.warning(f"{e = }")
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


def aggregate_kws_results(kws_segment_results):
    kws_segment_results = [json.loads(kws_result) for kws_result in kws_segment_results]
    result = defaultdict(list)
    for kws_segment_result in kws_segment_results:
        for key, value in kws_segment_result.items():
            result[key].extend(value)
    return result


def filter_kws_result(kws_result):
    if isinstance(kws_result, str):
        kws_result = json.loads(kws_result)
    kws_result = {
        key: [value for value in values if value["score"] > Algorithm.kws_threshold]
        for key, values in kws_result.items()
    }
    # filter residual keys: keywords w/o occurrence
    kws_result = {key: values for key, values in kws_result.items() if len(values)}
    return json.dumps(kws_result)


def get_sad_audio_buffer_duration(sad, fs):
    return sad.input_audio_buffer.shape[0] / fs


def get_kws_decoder():
    decoder = KWSDecoder(KWSConfig.alphabet, KWSConfig.blank_index)
    decoder.set_beam_width(KWSConfig.beam_width)
    decoder.set_beta(KWSConfig.beta)
    decoder.set_blank_index(KWSConfig.blank_index)
    decoder.set_max_gap(KWSConfig.max_gap)
    decoder.set_min_clip(KWSConfig.clip_char_prob)
    decoder.set_min_keyword_score(KWSConfig.min_keyword_score)
    decoder.set_top_n(KWSConfig.top_n)
    return decoder
