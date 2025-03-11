# helper functions

import datetime
import io
import json
import logging
import os
import re

import numpy as np
import pjsua2 as pj
import requests
import soundfile as sf
from minio import Minio
from redis import Redis

from custom_callbacks import Call
from config import CallbackAPIs, ObjectStorage, UserAgent
from database import db_session
from models import AMDRecord

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


def get_call_id(remote_uri):
    pattern = re.compile(r"<sip:[+]*(\d+)@")
    match_pattern = pattern.search(remote_uri)
    try:
        return match_pattern.group(1)
    except AttributeError:
        return "NEW-PATTERN:" + remote_uri


def detect_answering_machine(call: Call) -> None:
    """Detect answering machine."""
    logger = get_logger()
    pass


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


def store_metadata(file_path, metadata_dict):
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
    logger = get_call_id
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
        call_record = AMDRecord(
            metadata_dict["call_id"],
            now_date,
            now_time,
            metadata_dict["result"],
            metadata_dict["num_turns"],
            metadata_dict["dialed_number"],
            metadata_dict["duration"],
        )
        db_session.add(call_record)
        db_session.commit()
    except:
        logger.info("Cannot save metadata in database!")


def call_api_non_blocking(url, data, text_or_json, default, timeout_estimator):
    logger = get_logger()
    timeout = timeout_estimator(data)
    try:
        response = requests.get(url, data=data, timeout=timeout)
        if response.status_code != 200:
            response = None
    except requests.exceptions.Timeout:
        response = None
    if response is None:
        logger.warning(f"{url} latency is high")
        return default
    if text_or_json == "text":
        return response.text
    else:
        return response.json()


def call_api():
    logger = get_logger()
    logger.info("Calling API")
    call_api_non_blocking(CallbackAPIs.address, None, "text", "", lambda x: 1.0)


def delete_pj_obj_safely(pj_obj):
    try:
        del pj_obj
    except pj.Error:
        pass
