import logging
import os
import json_log_formatter


logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Enable json/structured logs when Datadog is enabled
if os.getenv("DD_TRACE_ENABLED", "false").lower() == 'true':
    formatter = json_log_formatter.VerboseJSONFormatter()
else:
    fmt = "%(levelname)s:     %(message)s"
    formatter = logging.Formatter(fmt)

handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)
