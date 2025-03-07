# helper functions

import logging
import re

from custom_callbacks import Call
from config import UserAgent

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
    pattern = re.compile(r'<sip:[+]*(\d+)@')
    match_pattern = pattern.search(remote_uri)
    try:
        return match_pattern.group(1)
    except AttributeError:
        return "NEW-PATTERN:" + remote_uri


def detect_answering_machine(call: Call) -> None:
    """Detect answering machine."""
    pass
