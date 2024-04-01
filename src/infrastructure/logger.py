import logging

fmt = "%(levelname)s:     %(message)s"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
formatter = logging.Formatter(fmt)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
handler.setFormatter(formatter)
logger.addHandler(handler)
