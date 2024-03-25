from enum import Enum


class MindloggerContentSource(str, Enum):
    """The allowed values for the Mindlogger-Content-Source HTTP header."""

    web = "web"
    admin = "admin"
    mobile = "mobile"
