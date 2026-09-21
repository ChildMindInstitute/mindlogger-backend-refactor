import pytest

from apps.authentication.services.security import AuthenticationService
from infrastructure.http.domain import MindloggerContentSource

DEFAULT = 30
WEB_ADMIN = 15


@pytest.mark.parametrize(
    "client",
    (MindloggerContentSource.web, MindloggerContentSource.admin),
)
def test_web_admin_use_short_lifetime_when_configured(client: MindloggerContentSource):
    assert AuthenticationService.token_expiration_minutes(client, DEFAULT, WEB_ADMIN) == WEB_ADMIN


@pytest.mark.parametrize(
    "client",
    (MindloggerContentSource.web, MindloggerContentSource.admin),
)
def test_web_admin_fall_back_to_default_when_unset(client: MindloggerContentSource):
    assert AuthenticationService.token_expiration_minutes(client, DEFAULT, None) == DEFAULT


@pytest.mark.parametrize("web_admin_minutes", (WEB_ADMIN, None))
@pytest.mark.parametrize("client", (MindloggerContentSource.mobile, None))
def test_mobile_and_unknown_always_use_default(client, web_admin_minutes):
    assert AuthenticationService.token_expiration_minutes(client, DEFAULT, web_admin_minutes) == DEFAULT
