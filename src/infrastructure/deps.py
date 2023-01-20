from fastapi import Header

from apps.shared.errors import BadRequestError


async def get_custom_header(custom_header: str = Header()):
    if custom_header != "Mindlogger-Content-Source":
        raise BadRequestError
    return custom_header
