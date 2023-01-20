from fastapi import Request

from apps.shared.errors import ForbiddenError
from infrastructure.http.domain import MindLoggerHeaders


async def mindlogger_headers(request: Request) -> MindLoggerHeaders:
    try:
        mindlogger_content_source = MindLoggerHeaders(
            mindlogger_content_source=request.headers.get(
                "mindlogger-content-source"
            )
        )
    except Exception:
        raise ForbiddenError

    return mindlogger_content_source
