# Configuration module for the answering machine detection project.

import logging
import os
from dataclasses import dataclass
from typing import ClassVar


is_production = False if os.getenv("UA_ENV") == "pc" else True


@dataclass
class AIEndpoints:
    endpoint_delay: float = 0.5 if is_production else 0.0
    base_prediction_url: str = os.getenv("AI_SERVICES_ADDRESS")
    am_endpoint: str = f"{base_prediction_url}acoustic_model"
    amd_kws_endpoint: str = f"{base_prediction_url}kws_for_amd"


@dataclass
class Database:
    user: str = os.getenv("DB_USER")
    password: str = os.getenv("DB_PASSWORD")
    host: str = os.getenv("DB_HOST")
    db_name: str = os.getenv("DB_NAME")
    url: str = f"postgresql+psycopg2://{user}:{password}@{host}/{db_name}"


@dataclass
class ObjectStorage:
    minio_url: str = os.getenv("MINIO_URL")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY")
    minio_wav_bucket_name: str = "wavs"
    minio_metadata_bucket_name: str = "metadata"


@dataclass
class UserAgent:
    max_inv_confirmed: float = 2
    max_media_consent: float = 10.0
    log_level: int = logging.DEBUG
    renew_time: float = 60


@dataclass
class Algorithm:
    max_call_duration: float = 3.0
    am_rft: float = 1 / 10
    asr_decoder_rtf: float = 1 / 10
    kws_rtf: float = 1 / 12
    redis_host: str = os.getenv("REDIS_HOST")
    redis_port: str = os.getenv("REDIS_PORT")


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
    blank_index: int = 0
