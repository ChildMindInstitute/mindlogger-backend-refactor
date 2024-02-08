import gettext
import os

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from config import settings
from infrastructure.http import get_language

gettext.bindtextdomain(gettext.textdomain(), settings.locale_dir)


class InternalizationMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        os.environ["LANG"] = get_language(request)
        return await call_next(request)
