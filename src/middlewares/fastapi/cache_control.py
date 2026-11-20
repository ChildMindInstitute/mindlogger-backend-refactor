from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class CacheControlMiddleware(BaseHTTPMiddleware):
    """Keeps API responses out of browser and shared caches.

    Responses carry per-user data, but caches key on the URL alone, so a stored one is replayed to
    whoever uses the browser next. Duplicating a tab is how this surfaces: Chrome treats it as a
    history navigation and serves those from cache without revalidating, so the new tab can be
    handed the previous user's identity while holding the current user's token.

    setdefault, not assignment: a route that set its own directive means something stricter by it.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        response.headers.setdefault("Cache-Control", "no-store")
        return response
