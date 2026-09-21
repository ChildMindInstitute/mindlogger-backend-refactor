from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

from apps.shared.test import BaseTest
from apps.users.domain import User
from middlewares import CacheControlMiddleware


class TestCacheControl(BaseTest):
    """Responses carry per-user data, and caches key on the URL alone, so storing one lets it be
    replayed to whoever uses the browser next. A duplicated tab is where this showed: Chrome serves
    those from cache without revalidating, so the new tab rendered the previous user while holding
    the current user's token.
    """

    async def test_user_response_is_not_stored(self, client, tom: User):
        client.login(tom)

        response = await client.get("/users/me")

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"

    async def test_workspaces_response_is_not_stored(self, client, tom: User):
        client.login(tom)

        response = await client.get("/workspaces")

        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"

    # The unauthorized answer comes from an exception handler rather than the route, which is why
    # the middleware is registered last and so wraps those too.
    async def test_unauthorized_response_is_not_stored(self, client):
        response = await client.get("/users/me")

        assert response.status_code == 401
        assert response.headers["cache-control"] == "no-store"


# A route that sets its own directive means something stricter by it, as the recovery code download
# does. Checked against a bare app, since reaching that endpoint needs a full MFA enrolment.
async def test_directive_set_by_the_route_is_kept():
    explicit = "no-store, no-cache, must-revalidate, private"
    app = FastAPI()
    app.add_middleware(CacheControlMiddleware)

    @app.get("/download")
    async def download() -> JSONResponse:
        return JSONResponse({}, headers={"Cache-Control": explicit})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test.com") as client:
        response = await client.get("/download")

    assert response.headers["cache-control"] == explicit
