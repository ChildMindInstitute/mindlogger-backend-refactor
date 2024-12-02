from enum import StrEnum


class MindloggerContentSource(StrEnum):
    """The allowed values for the Mindlogger-Content-Source HTTP header."""

    web = "web"
    admin = "admin"
    mobile = "mobile"
