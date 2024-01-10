import uuid

import pytest

from apps.applets.domain import AppletHistory
from apps.applets.service.applet_change import AppletChangeService
from apps.shared.enums import Language
from apps.shared.version import INITIAL_VERSION

# Just change minor
NEW_VERSION = INITIAL_VERSION.replace("0", "1")


@pytest.fixture
def applet() -> AppletHistory:
    return AppletHistory(display_name="Applet", version=INITIAL_VERSION)


@pytest.fixture
def new_applet() -> AppletHistory:
    return AppletHistory(display_name="Applet", version=NEW_VERSION)


@pytest.fixture
def applet_change_service(scope="module") -> AppletChangeService:
    return AppletChangeService()


def test_get_changes_theme_id_is_not_tracked(
    applet: AppletHistory,
    new_applet: AppletHistory,
    applet_change_service: AppletChangeService,
) -> None:
    new_applet.theme_id = uuid.uuid4()
    changes = applet_change_service.get_changes(applet, new_applet)
    assert not changes


def test_get_changes_not_set_fields_are_not_tracked(
    applet: AppletHistory,
    new_applet: AppletHistory,
    applet_change_service: AppletChangeService,
) -> None:
    changes = applet_change_service.get_changes(applet, new_applet)
    assert not changes


def test_get_changes_the_same_values_are_not_tracked(
    applet: AppletHistory,
    new_applet: AppletHistory,
    applet_change_service: AppletChangeService,
):
    applet.image = "test"
    new_applet.image = "test"
    changes = applet_change_service.get_changes(applet, new_applet)
    assert not changes


def test_get_changes_is_initial_applet_only_with_name(
    new_applet: AppletHistory,
    applet_change_service: AppletChangeService,
):
    changes = applet_change_service.get_changes(None, new_applet)
    assert len(changes) == 1
    assert changes[0] == f"Applet Name was set to {new_applet.display_name}"


@pytest.mark.parametrize(
    "field_name, value, change",
    (
        (
            "description",
            {"en": "NEW"},
            "Applet Description was set to NEW",
        ),
        (
            "about",
            {"en": "NEW"},
            "About Applet Page was set to NEW",
        ),
        ("image", "image", "Applet Image was set to image"),
        (
            "watermark",
            "watermark",
            "Applet Watermark was set to watermark",
        ),
        (
            "report_server_ip",
            "http://localhost",
            "Server URL was set to http://localhost",
        ),
        (
            "report_public_key",
            "public key",
            "Public encryption key was set to public key",
        ),
        (
            "report_recipients",
            ["test@example.com"],
            "Email recipients was set to test@example.com",
        ),
        (
            "report_include_user_id",
            True,
            "Include respondent in the Subject and Attachment was enabled",
        ),
        (
            "report_email_body",
            "email body",
            "Email Body was set to email body",
        ),
        (
            "stream_enabled",
            True,
            "Enable streaming of response data was enabled",
        ),
        (
            "stream_ip_address",
            "127.0.0.1",
            "Stream IP Address was set to 127.0.0.1",
        ),
        (
            "stream_port",
            8882,
            "Stream Port was set to 8882",
        ),
    ),
)
def test_get_changes_is_initial_version(
    new_applet: AppletHistory,
    applet_change_service: AppletChangeService,
    field_name: str,
    value: str | dict | bool | int,
    change: str,
):
    setattr(new_applet, field_name, value)
    changes = applet_change_service.get_changes(None, new_applet)
    assert len(changes) == 2
    assert changes[1] == change


@pytest.mark.parametrize(
    "field_name, value, change",
    (
        (
            "description",
            {"en": "NEW"},
            "Applet Description was set to NEW",
        ),
        (
            "about",
            {"en": "NEW"},
            "About Applet Page was set to NEW",
        ),
        ("image", "image", "Applet Image was set to image"),
        (
            "watermark",
            "watermark",
            "Applet Watermark was set to watermark",
        ),
        (
            "report_server_ip",
            "http://localhost",
            "Server URL was set to http://localhost",
        ),
        (
            "report_public_key",
            "public key",
            "Public encryption key was set to public key",
        ),
        (
            "report_recipients",
            ["test@example.com"],
            "Email recipients was set to test@example.com",
        ),
        (
            "report_include_user_id",
            True,
            "Include respondent in the Subject and Attachment was enabled",
        ),
        (
            "report_email_body",
            "email body",
            "Email Body was set to email body",
        ),
        (
            "stream_enabled",
            True,
            "Enable streaming of response data was enabled",
        ),
        (
            "stream_ip_address",
            "127.0.0.1",
            "Stream IP Address was set to 127.0.0.1",
        ),
        (
            "stream_port",
            8882,
            "Stream Port was set to 8882",
        ),
    ),
)
def test_get_changes_applet_updated(
    applet: AppletHistory,
    new_applet: AppletHistory,
    applet_change_service: AppletChangeService,
    field_name: str,
    value: str | dict | bool | int,
    change: str,
):
    setattr(new_applet, field_name, value)
    changes = applet_change_service.get_changes(applet, new_applet)
    assert len(changes) == 1
    assert changes[0] == change


def test_get_changes_new_applet_bool_fields_disabled(
    applet: AppletHistory,
    new_applet: AppletHistory,
    applet_change_service: AppletChangeService,
):
    applet.report_include_user_id = True
    applet.stream_enabled = True
    applet.stream_ip_address = "127.0.0.1"
    applet.stream_port = 8882

    new_applet.report_include_user_id = False
    new_applet.stream_enabled = False
    new_applet.stream_ip_address = None
    new_applet.stream_port = None

    changes = applet_change_service.get_changes(applet, new_applet)
    assert len(changes) == 4
    exp_changes = [
        "Enable streaming of response data was disabled",
        "Include respondent in the Subject and Attachment was disabled",
        "Stream IP Address was cleared",
        "Stream Port was cleared",
    ]
    for change in exp_changes:
        assert change in changes


def test_get_changes_new_applet_text_field_is_cleared(
    applet: AppletHistory,
    new_applet: AppletHistory,
    applet_change_service: AppletChangeService,
):
    applet.description = {Language.ENGLISH: "Description"}
    new_applet.description = {Language.ENGLISH: ""}
    changes = applet_change_service.get_changes(applet, new_applet)
    assert len(changes) == 1
    assert changes[0] == "Applet Description was cleared"


def test_get_changes_new_applet_text_field_was_changed(
    applet: AppletHistory,
    new_applet: AppletHistory,
    applet_change_service: AppletChangeService,
):
    applet.description = {Language.ENGLISH: "Description"}
    new_applet.description = {Language.ENGLISH: "New"}
    changes = applet_change_service.get_changes(applet, new_applet)
    assert len(changes) == 1
    assert changes[0] == "Applet Description was changed to New"


def test_compare_two_applets(
    applet: AppletHistory, applet_change_service: AppletChangeService
):
    change = applet_change_service.compare(applet, applet)
    assert change.display_name == f"New applet {applet.display_name} added"
    assert change.changes == [f"Applet Name was set to {applet.display_name}"]
    # For this test we can avoid business rule that activities are required
    assert not change.activities
    assert not change.activity_flows
