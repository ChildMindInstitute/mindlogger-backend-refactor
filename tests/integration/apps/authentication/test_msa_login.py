import datetime

import allure
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy import select
from starlette import status

from apps.authentication.router import router as auth_router
from apps.authentication.services.security import AuthenticationService
from apps.legal.db.schemas import LegalAcceptanceSchema
from apps.users import User
from config import settings

LOGIN_URL = auth_router.url_path_for("get_token")
MSA_ACCEPT_URL = auth_router.url_path_for("accept_msa_at_login")
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

    async def accept(self, app: FastAPI, user: User, version: str):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test.com") as client:
            return await client.post(
                MSA_ACCEPT_URL,
                json={"msaToken": AuthenticationService.create_msa_token(user.id), "msaVersion": version},
            )

    async def acceptances(self, db_session, user: User) -> list[LegalAcceptanceSchema]:
        query = select(LegalAcceptanceSchema).where(LegalAcceptanceSchema.user_id == user.id)
        return list((await db_session.scalars(query)).all())

    async def test_accept_at_login_returns_tokens(self, app: FastAPI, db_session, ferb_user: User):
        response = await self.accept(app, ferb_user, "2026-11-01")

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["result"]["token"]["accessToken"]
        rows = await self.acceptances(db_session, ferb_user)
        assert [row.source for row in rows] == ["login_prompt"]

    async def test_accept_at_login_rejects_outdated_version(self, app: FastAPI, db_session, ferb_user: User):
        response = await self.accept(app, ferb_user, "2025-01-01")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["error_code"] == "LEGAL.MSA_VERSION_OUTDATED"
        assert await self.acceptances(db_session, ferb_user) == []
