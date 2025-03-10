# helper functions

import logging
import os
import re

import numpy as np
import pjsua2 as pj
import soundfile as sf
from minio import Minio
from redis import Redis

from custom_callbacks import Call
from config import ObjectStorage, UserAgent

_logger = None


def get_logger(name: str = "AMD") -> logging.Logger:
    """Get logger."""
    global _logger
    if _logger is None:
        logging.basicConfig(
            format="USER-AGENT-LOG %(asctime)s\t%(levelname)s\t%(message)s",
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


def store_metadata():
    pass


def add_call_log_to_database():
    pass


def call_api():
    pass


def delete_pj_obj_safely():
    pass
