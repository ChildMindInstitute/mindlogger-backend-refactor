import logging

fmt = "%(levelname)s:     %(message)s"
logger = logging.getLogger("mindlogger_backend")
logger.setLevel(logging.INFO)
formatter = logging.Formatter(fmt)
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logger.addHandler(handler)
