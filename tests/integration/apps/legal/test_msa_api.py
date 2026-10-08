import datetime

import allure
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pytest_mock import MockerFixture
from sqlalchemy import select
from starlette import status

from apps.legal.constants import AcceptanceSource, LegalDocType
from apps.legal.crud import LegalAcceptancesCRUD
from apps.legal.db.schemas import LegalAcceptanceSchema
from apps.legal.domain import LegalAcceptanceCreate
from apps.legal.router import router as legal_router
from apps.users import User
from config import settings


@allure.epic("Legal")
@allure.feature("MSA version")
class TestMsaVersionApi:
    msa_version_url = legal_router.url_path_for("msa_version_get")
    msa_status_url = legal_router.url_path_for("msa_status_get")
    msa_accept_url = legal_router.url_path_for("msa_accept")

    async def test_msa_version_is_public(self, app: FastAPI, mocker: MockerFixture):
        mocker.patch.object(settings.legal, "msa_version", "2026-09-15")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test.com") as client:
            response = await client.get(self.msa_version_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["result"] == {"version": "2026-09-15"}

    async def test_msa_status_shows_grace_deadline(
        self, create_authorized_client, db_session, ferb_user: User, mocker: MockerFixture
    ):
        effective_from = datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(days=1)
        mocker.patch.object(settings.legal, "msa_version", "2026-11-01")
        mocker.patch.object(settings.legal, "msa_effective_from", effective_from)
        await LegalAcceptancesCRUD(db_session).create(
            LegalAcceptanceCreate(
                user_id=ferb_user.id,
                doc_type=LegalDocType.MSA,
                version="2025-01-01",
                accepted_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
                source=AcceptanceSource.SIGNUP,
            )
        )

        async with create_authorized_client(ferb_user) as client:
            response = await client.get(self.msa_status_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["result"] == {
            "status": "grace",
            "version": "2026-11-01",
            "deadline": str(effective_from + datetime.timedelta(days=60)),
        }

    async def test_msa_accept_saves_one_row(
        self, create_authorized_client, db_session, ferb_user: User, mocker: MockerFixture
    ):
        effective_from = datetime.datetime.now(datetime.timezone.utc).date() - datetime.timedelta(days=1)
        mocker.patch.object(settings.legal, "msa_version", "2026-11-01")
        mocker.patch.object(settings.legal, "msa_effective_from", effective_from)

        async with create_authorized_client(ferb_user) as client:
            await client.post(self.msa_accept_url, json={"msaVersion": "2026-11-01"})
            response = await client.post(self.msa_accept_url, json={"msaVersion": "2026-11-01"})

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["result"]["status"] == "accepted"
        rows = (
            await db_session.scalars(select(LegalAcceptanceSchema).where(LegalAcceptanceSchema.user_id == ferb_user.id))
        ).all()
        assert len(rows) == 1
        assert rows[0].source == "login_prompt"
