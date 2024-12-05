import logging
from ddtrace import tracer
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.types import EventDict, Processor
from asgi_correlation_id.context import correlation_id
from fastapi import FastAPI, Request, Response
from uvicorn.protocols.utils import get_path_with_query_string
import structlog
import time

# Much of this is borrowed from: https://gist.github.com/Brymes/cd8f9f138e12845417a246822f64ca26

# https://github.com/hynek/structlog/issues/35#issuecomment-591321744
def rename_event_key(_, __, event_dict: EventDict) -> EventDict:
    """
    Log entries keep the text message in the `event` field, but Datadog
    uses the `message` field. This processor moves the value from one field to
    the other.
    See https://github.com/hynek/structlog/issues/35#issuecomment-591321744
    """
    event_dict["message"] = event_dict.pop("event")
    return event_dict


def drop_color_message_key(_, __, event_dict: EventDict) -> EventDict:
    """
    Uvicorn logs the message a second time in the extra `color_message`, but we don't
    need it. This processor drops the key from the event dict if it exists.
    """
    event_dict.pop("color_message", None)
    return event_dict


def tracer_injection(_, __, event_dict: EventDict) -> EventDict:
    """
    Inject Datadog trace info into the event dict.
    """
    # get correlation ids from current tracer context
    span = tracer.current_span()
    trace_id, span_id = (span.trace_id, span.span_id) if span else (None, None)

    # add ids to structlog event dictionary
    event_dict["dd.trace_id"] = str(trace_id or 0)
    event_dict["dd.span_id"] = str(span_id or 0)

    return event_dict


def setup_logging(json_logs: bool = False, log_level: str = "INFO"):
    """
    Setup logging for the application.
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso")

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.stdlib.ExtraAdder(),
        drop_color_message_key,
        tracer_injection,
        timestamper,
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # We rename the `event` key to `message` only in JSON logs, as Datadog looks for the
        # `message` key but the pretty ConsoleRenderer looks for `event`
        shared_processors.append(rename_event_key)
        # Format the exception only for JSON logs, as we want to pretty-print them when
        # using the ConsoleRenderer
        shared_processors.append(structlog.processors.format_exc_info)

    structlog.configure(
        processors=shared_processors
                   + [
                       # Prepare event dict for `ProcessorFormatter`.
                       structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
                   ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    log_renderer: structlog.types.Processor
    if json_logs:
        log_renderer = structlog.processors.JSONRenderer()
    else:
        log_renderer = structlog.dev.ConsoleRenderer()

    formatter = structlog.stdlib.ProcessorFormatter(
        # These run ONLY on `logging` entries that do NOT originate within
        # structlog.
        foreign_pre_chain=shared_processors,
        # These run on ALL entries after the pre_chain is done.
        processors=[
            # Remove _record & _from_structlog.
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            log_renderer,
        ],
    )

    handler = logging.StreamHandler()
    # Use OUR `ProcessorFormatter` to format all `logging` entries.
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level.upper())

    for _log in ["uvicorn", "uvicorn.error"]:
        # Clear the log handlers for uvicorn loggers, and enable propagation
        # so the messages are caught by our root logger and formatted correctly
        # by structlog
        logging.getLogger(_log).handlers.clear()
        logging.getLogger(_log).propagate = True

    # Since we re-create the access logs ourselves, to add all information
    # in the structured log (see the `logging_middleware` in app.py), we clear
    # the handlers and prevent the logs to propagate to a logger higher up in the
    # hierarchy (effectively rendering them silent).
    logging.getLogger("uvicorn.access").handlers.clear()
    logging.getLogger("uvicorn.access").propagate = False

    # def handle_exception(exc_type, exc_value, exc_traceback):
    #     """
    #     Log any uncaught exception instead of letting it be printed by Python
    #     (but leave KeyboardInterrupt untouched to allow users to Ctrl+C to stop)
    #     See https://stackoverflow.com/a/16993115/3641865
    #     """
    #     if issubclass(exc_type, KeyboardInterrupt):
    #         sys.__excepthook__(exc_type, exc_value, exc_traceback)
    #         return
    #
    #     root_logger.error(
    #         "Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback)
    #     )
    #
    # sys.excepthook = handle_exception


# async def logging_middleware(request: Request, call_next) -> Response:

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        structlog.contextvars.clear_contextvars()
        # These context vars will be added to all log entries emitted during the request
        request_id = correlation_id.get()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter_ns()
        # If the call_next raises an error, we still want to return our own 500 response,
        # so we can add headers to it (process time, request ID...)
        response = Response(status_code=500)

        try:
            response = await call_next(request)
        except Exception as e:
            # TODO: Validate that we don't swallow exceptions (unit test?)
            structlog.stdlib.get_logger("api.error").exception("Uncaught exception")
            raise e
        finally:
            access_logger = structlog.stdlib.get_logger("api.access")
            process_time = time.perf_counter_ns() - start_time
            status_code = response.status_code
            url = get_path_with_query_string(request.scope)
            client_host = request.client.host
            client_port = request.client.port
            http_method = request.method
            http_version = request.scope["http_version"]
            # Recreate the Uvicorn access log format, but add all parameters as structured information

            if 400 < status_code < 500:
                access_logger.warn(
                    f"""{client_host}:{client_port} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
                    http={
                        "url": str(request.url),
                        "status_code": status_code,
                        "method": http_method,
                        "request_id": request_id,
                        "version": http_version,
                    },
                    network={"client": {"ip": client_host, "port": client_port}},
                    duration=process_time,
                )
            else:
                access_logger.info(
                    f"""{client_host}:{client_port} - "{http_method} {url} HTTP/{http_version}" {status_code}""",
                    http={
                        "url": str(request.url),
                        "status_code": status_code,
                        "method": http_method,
                        "request_id": request_id,
                        "version": http_version,
                    },
                    network={"client": {"ip": client_host, "port": client_port}},
                    duration=process_time,
                )
            # response.headers["X-Process-Time"] = str(process_time / 10 ** 9)
            return response
