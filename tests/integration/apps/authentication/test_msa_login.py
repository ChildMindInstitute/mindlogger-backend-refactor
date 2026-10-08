import datetime

import allure
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest_mock import MockerFixture
from starlette import status

from apps.authentication.router import router as auth_router
from config import settings

LOGIN_URL = auth_router.url_path_for("get_token")
PASSWORD = "Str0ngPass!word"


@allure.epic("Legal")
@allure.feature("MSA at login")
class TestMsaLogin:
    @pytest.fixture(autouse=True)
    def msa_enforced(self, mocker: MockerFixture):
        mocker.patch("apps.authentication.api.auth.log")
        mocker.patch.object(settings.legal, "msa_version", "2026-11-01")
        effective_from = datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(days=1)
        mocker.patch.object(settings.legal, "msa_effective_from", effective_from)

    @pytest.fixture
    async def user_email(self, user_create_service, user_create_factory) -> str:
        user_create = user_create_factory.build(first_name="Candace", last_name="Flynn", password=PASSWORD)
        await user_create_service(user_create)
        return user_create.email

    async def login(self, app: FastAPI, email: str, client_source: str) -> dict:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test.com") as client:
            response = await client.post(
                LOGIN_URL,
                json={"email": email, "password": PASSWORD},
                headers={"Mindlogger-Content-Source": client_source},
            )
        assert response.status_code == status.HTTP_200_OK
        return response.json()["result"]

    async def test_admin_login_requires_msa(self, app: FastAPI, user_email: str):
        result = await self.login(app, user_email, "admin")

        assert result["msaRequired"] is True
        assert result["msaToken"]
        assert result["version"] == "2026-11-01"
        assert "token" not in result

    async def test_web_login_is_not_blocked(self, app: FastAPI, user_email: str):
        result = await self.login(app, user_email, "web")

        assert result["token"]["accessToken"]
