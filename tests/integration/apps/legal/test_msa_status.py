import datetime

import allure
import pytest
from pytest_mock import MockerFixture

from apps.legal.constants import AcceptanceSource, LegalDocType, MsaStatus
from apps.legal.crud import LegalAcceptancesCRUD
from apps.legal.domain import LegalAcceptanceCreate
from apps.legal.service import LegalAcceptanceService
from apps.users import User
from config import settings

TODAY = datetime.datetime.now(datetime.timezone.utc).date()
EFFECTIVE_FROM = TODAY - datetime.timedelta(days=1)


async def add_acceptance(db_session, user: User, version: str) -> None:
    await LegalAcceptancesCRUD(db_session).create(
        LegalAcceptanceCreate(
            user_id=user.id,
            doc_type=LegalDocType.MSA,
            version=version,
            accepted_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
            source=AcceptanceSource.SIGNUP,
        )
    )


@allure.epic("Legal")
@allure.feature("MSA status")
class TestMsaStatus:
    @pytest.fixture(autouse=True)
    def msa_settings(self, mocker: MockerFixture):
        mocker.patch.object(settings.legal, "msa_version", "2026-11-01")
        mocker.patch.object(settings.legal, "msa_effective_from", EFFECTIVE_FROM)
        mocker.patch.object(settings.legal, "msa_grace_days", 60)

    async def test_accepted_current_version(self, db_session, ferb_user: User):
        await add_acceptance(db_session, ferb_user, "2026-11-01")

        result = await LegalAcceptanceService(db_session).get_msa_status(ferb_user.id)

        assert result.status == MsaStatus.ACCEPTED

    async def test_accepted_earlier_version_is_in_grace(self, db_session, ferb_user: User):
        await add_acceptance(db_session, ferb_user, "2025-01-01")

        result = await LegalAcceptanceService(db_session).get_msa_status(ferb_user.id)

        assert result.status == MsaStatus.GRACE
        assert result.deadline == EFFECTIVE_FROM + datetime.timedelta(days=60)

    async def test_no_acceptance_is_required(self, db_session, ferb_user: User):
        result = await LegalAcceptanceService(db_session).get_msa_status(ferb_user.id)

        assert result.status == MsaStatus.REQUIRED

    async def test_signed_up_before_cutoff_is_in_grace(self, db_session, ferb_user: User, mocker: MockerFixture):
        mocker.patch.object(settings.legal, "msa_grace_signup_cutoff", TODAY + datetime.timedelta(days=1))

        result = await LegalAcceptanceService(db_session).get_msa_status(ferb_user.id)

        assert result.status == MsaStatus.GRACE

    async def test_signed_up_on_cutoff_day_is_required(self, db_session, ferb_user: User, mocker: MockerFixture):
        mocker.patch.object(settings.legal, "msa_grace_signup_cutoff", TODAY)

        result = await LegalAcceptanceService(db_session).get_msa_status(ferb_user.id)

        assert result.status == MsaStatus.REQUIRED
