# helper functions

import logging

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


def detect_answering_machine(call: Call) -> None:
    """Detect answering machine."""
    pass
