import logging
import os
import json_log_formatter
import ddtrace
from ddtrace import tracer

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class DataDogJSONFormatter(json_log_formatter.JSONFormatter):
    def json_record(self, message, extra, record) -> dict:
        extra = super().json_record(message, extra, record)
        # extra['user_id'] = current_user_id()
        # extra['ip'] = current_ip()

        # Include builtins
        extra['level'] = record.levelname
        extra['name'] = record.name

        span = tracer.current_span()
        trace_id, span_id = (str((1 << 64) - 1 & span.trace_id), span.span_id) if span else (None, None)

        extra['dd.trace_id'] = str(trace_id or 0)
        extra['dd.span_id'] = str(span_id or 0)


        extra['dd.env'] = ddtrace.config.env or ""
        extra['dd.service'] = ddtrace.config.service or ""
        extra['dd.version'] = ddtrace.config.version or ""

        return extra


# Enable json/structured logs when Datadog is enabled
if os.getenv("DD_TRACE_ENABLED", "false").lower() == 'true':
    # formatter = json_log_formatter.VerboseJSONFormatter()
    formatter = DataDogJSONFormatter()
else:
    fmt = "%(levelname)s:     %(message)s"
    formatter = logging.Formatter(fmt)

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)
