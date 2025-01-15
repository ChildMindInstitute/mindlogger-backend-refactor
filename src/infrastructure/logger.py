import logging
import os

import structlog


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
    logger = structlog.stdlib.get_logger("api")  # type: ignore


