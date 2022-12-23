from fastapi import Request, Response
from starlette.middleware.base import (
    BaseHTTPMiddleware,
    RequestResponseEndpoint,
)

from infrastructure.database.core import transaction


class DatabaseTransactionMiddleware(BaseHTTPMiddleware):
    @transaction.commit
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        return await call_next(request)
