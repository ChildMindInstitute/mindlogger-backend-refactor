import logging
import os

import structlog
from pydantic.tools import parse_obj_as

from infrastructure.datadog import setup_structured_logging

if os.environ.get("ENV") == "testing":
    # Some tests check logging output, so use the old logger
    fmt = "%(levelname)s:     %(message)s"
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(fmt)
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
else:
    # Default to structured logger, enable JSON format if env set
    LOG_JSON_FORMAT = parse_obj_as(bool, os.getenv("LOG_JSON_FORMAT", False))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    setup_structured_logging(json_logs=LOG_JSON_FORMAT, log_level=LOG_LEVEL)
    logger = structlog.stdlib.get_logger("api")
