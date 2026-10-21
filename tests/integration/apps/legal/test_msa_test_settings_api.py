import datetime

import allure
import pytest
from pytest_mock import MockerFixture
from starlette import status

from apps.legal.cache import MsaTestSettingsCache
from apps.legal.constants import MsaStatus
from apps.legal.router import router as legal_router
from apps.legal.service import LegalAcceptanceService, msa_today
from apps.users import User
from config import settings

TODAY = msa_today()


@allure.epic("Legal")
@allure.feature("MSA test settings")
class TestMsaTestSettingsApi:
    test_settings_url = legal_router.url_path_for("msa_test_settings_put")

    @pytest.fixture(autouse=True)
    async def clear_test_settings(self, ferb_user: User):
        yield
        await MsaTestSettingsCache().delete(ferb_user.id)

    async def test_put_changes_only_my_status(
        self, create_authorized_client, db_session, ferb_user: User, perry_user: User, mocker: MockerFixture
    ):
        mocker.patch.object(settings.legal, "msa_test_overrides_enabled", True)
        body = {
            "effectiveFrom": str(TODAY - datetime.timedelta(days=70)),
            "graceDays": 60,
            "graceSignupCutoff": str(TODAY + datetime.timedelta(days=1)),
        }

        async with create_authorized_client(ferb_user) as client:
            response = await client.put(self.test_settings_url, json=body)

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["result"]["status"] == "required"
        assert response.json()["result"]["deadline"] == str(TODAY - datetime.timedelta(days=11))
        # Enforcement is off in the normal settings, so another user is unaffected
        other = await LegalAcceptanceService(db_session).get_msa_status(perry_user.id)
        assert other.status == MsaStatus.ACCEPTED

    async def test_put_is_not_found_when_disabled(self, create_authorized_client, ferb_user: User):
        async with create_authorized_client(ferb_user) as client:
            response = await client.put(self.test_settings_url, json={"graceDays": 60})

        assert response.status_code == status.HTTP_404_NOT_FOUND
