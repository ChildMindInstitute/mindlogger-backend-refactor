from typing import Callable

from fastapi import HTTPException
from starlette import status
from starlette.types import ASGIApp


class ContentLengthLimitMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        content_length_limit: int | None = None,
        methods: list | None = None,
    ):
        self.app = app
        self.content_length_limit = content_length_limit
        self.methods = methods

    def method_matches(self, method):
        if self.methods:
            return method in self.methods
        return True

    async def __call__(self, scope, receive, send):
        if not (
            scope["type"] == "http"
            and self.method_matches(scope.get("method"))
            and self.content_length_limit is not None
        ):
            await self.app(scope, receive, send)
            return

        def _receiver() -> Callable:
            read_length: int = 0

            async def __receive():
                nonlocal read_length, receive

                message = await receive()
                if message["type"] == "http.request":
                    read_length += len(message.get("body", b""))
                    if read_length > self.content_length_limit:
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE  # noqa: E501
                        )
                return message

            return __receive

        _receive = _receiver()
        await self.app(scope, _receive, send)
