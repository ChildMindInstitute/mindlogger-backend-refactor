import allure
from pytest_mock import MockerFixture
from sqlalchemy import select
from starlette.requests import Request

from apps.legal.constants import AcceptanceSource, LegalDocType
from apps.legal.db.schemas import LegalAcceptanceSchema
from apps.legal.service import LegalAcceptanceService
from apps.users import User
from config import settings


def make_request(headers: dict[str, str] | None = None, client: tuple[str, int] | None = None) -> Request:
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({"type": "http", "headers": raw_headers, "client": client})


@allure.epic("Legal")
@allure.feature("MSA acceptance")
class TestLegalAcceptanceService:
    async def test_accept_msa_saves_row(self, db_session, ferb_user: User, mocker: MockerFixture):
        mocker.patch.object(settings.legal, "msa_version", "2026-09-15")
        request = make_request(
            headers={"Mindlogger-Content-Source": "admin", "User-Agent": "test-agent"},
            client=("203.0.113.7", 1234),
        )

        acceptance = await LegalAcceptanceService(db_session).accept_msa(ferb_user.id, AcceptanceSource.SIGNUP, request)

        rows = (
            await db_session.scalars(select(LegalAcceptanceSchema).where(LegalAcceptanceSchema.user_id == ferb_user.id))
        ).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.id == acceptance.id
        assert row.doc_type == LegalDocType.MSA
        assert row.version == "2026-09-15"
        assert row.source == AcceptanceSource.SIGNUP
        assert row.client_source == "admin"
        assert row.ip_address == "203.0.113.7"
        assert row.user_agent == "test-agent"
        assert row.accepted_at is not None

    async def test_accept_msa_without_request_details(self, db_session, ferb_user: User):
        acceptance = await LegalAcceptanceService(db_session).accept_msa(
            ferb_user.id, AcceptanceSource.SIGNUP, make_request()
        )

        assert acceptance.client_source is None
        assert acceptance.ip_address is None
        assert acceptance.user_agent is None

    async def test_accept_msa_keeps_history(self, db_session, ferb_user: User, mocker: MockerFixture):
        service = LegalAcceptanceService(db_session)
        mocker.patch.object(settings.legal, "msa_version", "2026-09-15")
        await service.accept_msa(ferb_user.id, AcceptanceSource.SIGNUP, make_request())
        mocker.patch.object(settings.legal, "msa_version", "2027-03-01")
        await service.accept_msa(ferb_user.id, AcceptanceSource.SIGNUP, make_request())

        versions = (
            await db_session.scalars(
                select(LegalAcceptanceSchema.version).where(LegalAcceptanceSchema.user_id == ferb_user.id)
            )
        ).all()
        assert sorted(versions) == ["2026-09-15", "2027-03-01"]
