import uuid

import allure
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy import select
from starlette import status

from apps.legal.constants import AcceptanceSource, LegalDocType
from apps.legal.db.schemas import LegalAcceptanceSchema
from apps.users.router import router as user_router
from config import settings

USER_CREATE_URL = user_router.url_path_for("user_create")


def signup_payload(**extra) -> dict:
    return {
        "email": f"{uuid.uuid4().hex[:8]}@getting.com",
        "firstName": "Candace",
        "lastName": "Flynn",
        "password": "Str0ngPass!word",
        **extra,
    }


async def get_acceptances(db_session, user_id: str) -> list[LegalAcceptanceSchema]:
    query = select(LegalAcceptanceSchema).where(LegalAcceptanceSchema.user_id == uuid.UUID(user_id))
    return list((await db_session.scalars(query)).all())


@allure.epic("Legal")
@allure.feature("MSA acceptance")
class TestUserCreateMsa:
    @pytest.fixture(autouse=True)
    def mock_audit_log(self, mocker: MockerFixture):
        mocker.patch("apps.users.api.users.log")

    async def test_signup_with_msa_accepted_saves_acceptance(self, app: FastAPI, db_session, mocker: MockerFixture):
        mocker.patch.object(settings.legal, "msa_version", "2026-09-15")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test.com") as client:
            response = await client.post(
                USER_CREATE_URL,
                json=signup_payload(msaAccepted=True),
                headers={"Mindlogger-Content-Source": "admin"},
            )

        assert response.status_code == status.HTTP_201_CREATED
        acceptances = await get_acceptances(db_session, response.json()["result"]["id"])
        assert len(acceptances) == 1
        assert acceptances[0].doc_type == LegalDocType.MSA
        assert acceptances[0].version == "2026-09-15"
        assert acceptances[0].source == AcceptanceSource.SIGNUP
        assert acceptances[0].client_source == "admin"

    @pytest.mark.parametrize("extra", [{}, {"msaAccepted": False}])
    async def test_signup_without_msa_accepted_saves_nothing(self, app: FastAPI, db_session, extra: dict):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test.com") as client:
            response = await client.post(USER_CREATE_URL, json=signup_payload(**extra))

        assert response.status_code == status.HTTP_201_CREATED
        assert await get_acceptances(db_session, response.json()["result"]["id"]) == []
