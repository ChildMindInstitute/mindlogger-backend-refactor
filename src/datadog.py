import logging
import os

from pydantic.tools import parse_obj_as

from infrastructure.dependency.structured_logs import setup_structured_logging

# Import DataDog tracer ASAP
if os.getenv("DD_TRACE_ENABLED", "false").lower() == "true":
    logger = logging.getLogger("startup")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    logger.info("Enabling Datadog")
    # import ddtrace.auto  # noqa
    from ddtrace import config, patch

    # Manually patch.  The auto patcher throws some errors in AMQP (which it doesn't support so why patch it??)
    patch(
        sqlalchemy=True,
        fastapi=True,
        botocore=True,
        asyncpg=True,
        httpx=True,
        jinja2=True,
        requests=True,
        starlette=True,
        structlog=True,
        futures=True,
        gevent=True,
        redis=True,
    )
    config.botocore["distributed_tracing"] = True

    LOG_JSON_FORMAT = parse_obj_as(bool, os.getenv("LOG_JSON_FORMAT", False))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    setup_structured_logging(json_logs=LOG_JSON_FORMAT, log_level=LOG_LEVEL)

    logger.info("Structured logging configured")
