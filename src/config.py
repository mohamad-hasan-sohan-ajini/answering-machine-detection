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
    max_call_duration: float = 15.0
    zero_padding: int = 4000
    max_tail_sil: float = 1.5
    lookahead_sil: float = 0.7
    am_rft: float = 1 / 10
    asr_decoder_rtf: float = 1 / 10
    kws_rtf: float = 1 / 12
    redis_host: str = os.getenv("REDIS_HOST")
    redis_port: str = os.getenv("REDIS_PORT")
    receiving_active_segment_sleep: float = 0.3
    receiving_silent_segment_sleep: float = 1.0


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


am_keywords = [
    "TO CONTINUE",
    "LOCATED",
    "RECORDED",
    "IS LOCATED",
    "THE GREAT PRAIRIES",
    "FOLLOWING MENU",
    "IF YOU KNOW YOUR PARTY",
    "AUTOMATIC VOICE MESSAGE",
    "THE NUMBER YOU HAVE DIALED",
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
    "NO ONE IS AVAILABLE",
    "HAS BEEN DISCONNECTED",
    "SATISFIED WITH YOUR MESSAGE",
    "TOUCH STAR",
    "GET YOUR MESSAGE",
    "OPTION IS INVALID",
    "PLEASE TRY AGAIN",
    "PLEASE LEAVE YOUR",
    "LISTEN CAREFULLY",
    "CALLS ARE RECORDED",
    "ASSISTING OTHER CUSTOMERS",
    "CREATE A SUPPORT TICKET",
    "AT THE TONE",
    "AFTER THE BEEP",
    "FOR MORE OPTIONS",
    "WE ARE UNAVAILABLE",
    "LEAVE A VOICEMAIL",
    "CALL IS BEING TRANSFERRED",
    "NEXT AVAILABLE AGENT",
    "UNABLE TO ANSWER",
    "DURING BUSINESS HOURS",
    "IF YOU'D LIKE TO TRY OUR",
    "IS CLOSED",
    "IS NOW CLOSED",
    "CALL IS BEING RECORDED",
    "PLEASE DIAL",
    "LEAVING A VOICEMAIL",
    "SENDING AN EMAIL",
    "ANSWERING MACHINE",
    "CURRENTLY ON THE PHONE",
    "YOUR ENTRY WAS NOT",
    "HAS BEEN FORWARDED",
    "TRANSFER YOU CALL",
    "TRY YOUR CALL",
    "YOU ARE TRYING TO REACH",
    "GET BACK TO YOU",
    "IS NOT A VALID EXTENSION",
    "VISIT US ONLINE",
    "FOR QUALITY ASSURANCE",
    "DOT COM",
    "UNABLE TO COME TO THE PHONE",
    "BEING TRANSFERRED TO",
    "TELEPHONE NUMBER",
    "LEAVE YOUR NAME",
    "NOT IN SERVICE",
    "TRY TO CONNECT YOU",
    "TELEPHONE KEYPAD",
    "THIS IS THE ANSWERING SERVICE",
    "YOUR PARTY'S EXTENSION",
    "YOUR PARTIES EXTENSION",
    "CONTINUING TO HOLD",
    "FOR GENERAL QUERIES",
    "NOT ABLE TO TAKE",
    "YOUR PHONE CALL",
    "YOU'VE REACHED",
    "YOU HAVE REACHED",
    "WE ARE CURRENTLY",
    "BUSINESS HOURS",
    "OFFICE HOURS",
    "ARE CLOSED",
    "HOURS ARE AS FOLLOWS",
    "MONDAY FROM",
    "A WEEK",
    "ENTER YOUR",
    "ENTER THE",
    "ADDRESS IS",
    "AM EVERYDAY",
    "PM EVERYDAY",
    "AM EVERY DAY",
    "PM EVERY DAY",
    "DISCONNECTED",
    "STORE HOURS",
    "HOURS OF OPERATION",
    "FROM NINE AM",
    "FROM TEN AM",
    "FROM ELEVEN AM",
    "TO FIVE PM",
    "TO SIX PM",
    "TO SEVEN PM",
    "TO EIGHT PM",
    "TO NINE PM",
    "PLEASE BEGIN SPELLING",
    "SPANIOL OPREMADOS",
    "NINE AM TO",
    "EIGHT AM TO",
    "NINE AM TO",
    "TEN AM TO",
    "ELEVEN AM TO",
    "CONTINUED AN ESPANIOLO",
    "MONDAY THROUGH SUNDAY",
    "MONDAY THROUGH SATURDAY",
    "MONDAY THROUGH FRIDAY",
    "A RECORDING",
    "THE GOOGLE SUBSCRIBER",
]
