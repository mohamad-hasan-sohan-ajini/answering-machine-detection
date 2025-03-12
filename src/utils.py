# helper functions

import datetime
import io
import json
import logging
import os
import re
import time

import numpy as np
import pjsua2 as pj
import requests
import soundfile as sf
from minio import Minio
from redis import Redis

from custom_callbacks import Call
from config import Algorithm, CallbackAPIs, ObjectStorage, UserAgent
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


def get_call_id(remote_uri):
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


def detect_answering_machine(call: Call) -> None:
    """Detect answering machine."""
    logger = get_logger()
    call_id = call.getInfo().callIdString
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

    # each packet appended every 100-120 ms (jitter absolutely possible!)
    sad = None
    t0 = time.time()
    while time.time() - t0 < Algorithm.max_call_duration:
        if sad is None:
            sad = SAD()
        time.sleep(0.01)
    appended_bytes = wav_file.read()
    audio_buffer = parse_new_frames(appended_bytes, wav_info)
    zero_buffer = np.zeros(Algorithm.zero_padding, dtype=np.float32)
    audio_buffer = np.concatenate((zero_buffer, audio_buffer, zero_buffer))
    data = convert_np_array_to_wav_file_bytes(audio_buffer, fs)
    sad_result = sad.handle([data])[0]


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
