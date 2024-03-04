from fastapi import Request

from infrastructure.http.domain import MindloggerContentSource


async def get_mindlogger_content_source(
    request: Request,
) -> MindloggerContentSource:
    """Fetch the Mindlogger-Content-Source HTTP header."""

    try:
        return getattr(
            MindloggerContentSource,
            request.headers.get("mindlogger-content-source", MindloggerContentSource.web.name),
        )
    except AttributeError:
        return MindloggerContentSource.web


def get_language(request: Request) -> str:
    return request.headers.get("Content-Language", "en-US").split("-")[0]
