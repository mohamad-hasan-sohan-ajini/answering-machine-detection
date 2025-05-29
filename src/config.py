# Configuration module for the answering machine detection project.

import logging
import os
from dataclasses import dataclass
from typing import ClassVar

from dotenv import load_dotenv

load_dotenv()
is_production = False if os.getenv("UA_ENV") == "pc" else True


@dataclass
class AIEndpoints:
    endpoint_delay: float = 0.5 if is_production else 0.0
    base_prediction_url: str = os.getenv("AI_SERVICES_ADDRESS")
    am_endpoint: str = f"{base_prediction_url}acoustic_model"
    asr_decoder_endpoint: str = f"{base_prediction_url}asr_decoder"
    amd_kws_endpoint: str = f"{base_prediction_url}kws_for_amd"
    timeout: float = 1


@dataclass
class Database:
    user: str = os.getenv("DB_USER")
    password: str = os.getenv("DB_PASSWORD")
    host: str = os.getenv("DB_HOST")
    db_name: str = os.getenv("DB_NAME")
    table_name: str = os.getenv("DB_TABLE")
    url: str = f"postgresql+psycopg2://{user}:{password}@{host}/{db_name}"
    timeout: int = 500  # database timeout in milliseconds


@dataclass
class ObjectStorage:
    minio_url: str = os.getenv("MINIO_URL")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY")
    minio_wav_bucket_name: str = "wavs"
    minio_metadata_bucket_name: str = "metadata"


@dataclass
class UserAgent:
    max_inv_confirmed: float = 2.0
    max_media_consent: float = 1.0
    log_level: int = logging.DEBUG
    renew_time: float = 60


@dataclass
class Algorithm:
    chunk_interval: float = 0.1
    max_call_duration: float = 15.0
    zero_padding: int = 4000
    max_tail_sil: float = 1.0
    lookahead_sil: float = 0.2
    am_rft: float = 1 / 10
    asr_decoder_rtf: float = 1 / 10
    kws_rtf: float = 1 / 12
    redis_host: str = os.getenv("REDIS_HOST")
    redis_port: str = os.getenv("REDIS_PORT")
    expiration_time_second: int = 6000
    receiving_active_segment_sleep: float = 0.1
    receiving_silent_segment_sleep: float = 1.0
    max_awaiting_ai: float = 1.5
    kws_threshold: float = 0.15


@dataclass
class CallbackAPIs:
    address: str = os.getenv("CALLBACK_API_ADDRESS")


@dataclass
class KWSConfig:
    alphabet: ClassVar[list[str]] = [
        "-",
        " ",
        "'",
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
    ]
    num_labels: int = len(alphabet)
    blank_index: int = 0
    beam_width: int = 16
    beta: float = 1.05
    top_n: int = 25
    min_keyword_score: float = 1e-4
    max_gap: int = 25
    clip_char_prob: float = 0.01
    am_keywords: ClassVar[list[str]] = [
        "LEAVE YOUR NAME",
        "LEAVE A NAME",
        "LEAVE ME",
        "LEAVE US",
        "PHONE NUMBER",
        "YOUR NUMBER",
        "A NUMBER",
        "RETURN YOUR CALL",
        "AS SOON AS POSSIBLE",
        "GET BACK TO YOU",
        "AT THE TONE",
        "A MESSAGE",
        "YOUR MESSAGE",
        "CALL YOU",
        "RIGHT NOW",
        "UNFORTUNATELY",
        "REACHED",
        "A GREAT DAY",
        "A WONDERFUL DAY",
        "VE REACHED",
        "OFFICE HOURS",
        "FROM MONDAY",
        "MONDAY TO",
        "MONDAY THROUGH",
        "BUSINESS HOURS",
        "TAKE YOUR CALL",
        "CALL BACK",
        "ANSWER YOUR",
        "UNABLE",
        "IF YOU KNOW",
        "TO CONTINUE",
        "VE DIALED",
        "PRESS ONE",
        "PRESS TWO",
        "PRESS THREE",
        "PRESS FOUR",
        "PRESS FIVE",
        "PRESS SIX",
        "PRESS SEVEN",
        "PRESS EIGHT",
        "PRESS NINE",
        "PRESS ZERO",
        "PRESS POUND",
        "PRESS STAR",
        "RECORDED",
        "AFTER THE BEEP",
        "UNAVAILABLE",
        "IS CLOSED",
        "ARE CLOSED",
        "NOW CLOSED",
        "AN EMAIL",
        "ANSWERING MACHINE",
        "NOT IN SERVICE",
        "IS LOCATED",
        "ELEVEN AM TO",
        "TEN AM TO",
        "NINE AM TO",
        "EIGHT AM TO",
        "SEVEN AM TO",
        "SEVEN THIRTY AM TO",
        "TO FIVE PM",
        "TO SIX PM",
        "TO SEVEN PM",
        "TO EIGHT PM",
        "TO NINE PM",
    ]
