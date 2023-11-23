import uuid

import pytest

from apps.applets.domain import AppletHistory
from apps.applets.service.applet_change import AppletChangeService
from apps.shared.enums import Language


@pytest.fixture
def old_applet_history() -> AppletHistory:
    return AppletHistory(display_name="Applet")


@pytest.fixture
def new_applet_history() -> AppletHistory:
    return AppletHistory(display_name="Applet")


@pytest.fixture
def applet_change_service(scope="module") -> AppletChangeService:
    return AppletChangeService()


def test_theme_id_is_not_tracked(
    old_applet_history: AppletHistory,
    new_applet_history: AppletHistory,
    applet_change_service: AppletChangeService,
):
    new_applet_history.theme_id = uuid.uuid4()
    changes = applet_change_service.compare(
        new_applet_history, old_applet_history
    )
    assert not changes


def test_not_set_fields_are_not_tracked(
    old_applet_history: AppletHistory,
    new_applet_history: AppletHistory,
    applet_change_service: AppletChangeService,
):
    changes = applet_change_service.compare(
        new_applet_history, old_applet_history
    )
    assert not changes


def test_the_same_values_are_not_tracked(
    old_applet_history: AppletHistory,
    new_applet_history: AppletHistory,
    applet_change_service: AppletChangeService,
):
    old_applet_history.image = "test"
    new_applet_history.image = "test"
    changes = applet_change_service.compare(
        new_applet_history, old_applet_history
    )
    assert not changes


def test_is_initial_applet_only_with_name(
    new_applet_history: AppletHistory,
    applet_change_service: AppletChangeService,
):
    changes = applet_change_service.compare(None, new_applet_history)
    assert len(changes) == 1
    assert (
        changes[0]
        == f"Applet Name was set to {new_applet_history.display_name}"
    )


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
    ),
)
def test_is_initial_version(
    new_applet_history: AppletHistory,
    applet_change_service: AppletChangeService,
    field_name: str,
    value: str | dict | bool,
    change: str,
):
    setattr(new_applet_history, field_name, value)
    changes = applet_change_service.compare(None, new_applet_history)
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
    ),
)
def test_applet_updated(
    old_applet_history: AppletHistory,
    new_applet_history: AppletHistory,
    applet_change_service: AppletChangeService,
    field_name: str,
    value: str | dict | bool,
    change: str,
):
    setattr(new_applet_history, field_name, value)
    changes = applet_change_service.compare(
        old_applet_history, new_applet_history
    )
    assert len(changes) == 1
    assert changes[0] == change


def test_new_applet_bool_fields_disabled(
    old_applet_history: AppletHistory,
    new_applet_history: AppletHistory,
    applet_change_service: AppletChangeService,
):
    old_applet_history.report_include_user_id = True
    old_applet_history.stream_enabled = True
    new_applet_history.report_include_user_id = False
    new_applet_history.stream_enabled = False
    changes = applet_change_service.compare(
        old_applet_history, new_applet_history
    )
    assert len(changes) == 2
    exp_changes = [
        "Enable streaming of response data was disabled",
        "Include respondent in the Subject and Attachment was disabled",
    ]
    for change in exp_changes:
        assert change in changes


def test_new_applet_text_field_is_cleared(
    old_applet_history: AppletHistory,
    new_applet_history: AppletHistory,
    applet_change_service: AppletChangeService,
):
    old_applet_history.description = {Language.ENGLISH: "Description"}
    new_applet_history.description = {Language.ENGLISH: ""}
    changes = applet_change_service.compare(
        old_applet_history, new_applet_history
    )
    assert len(changes) == 1
    assert changes[0] == "Applet Description was cleared"


def test_new_applet_text_field_was_changed(
    old_applet_history: AppletHistory,
    new_applet_history: AppletHistory,
    applet_change_service: AppletChangeService,
):
    old_applet_history.description = {Language.ENGLISH: "Description"}
    new_applet_history.description = {Language.ENGLISH: "New"}
    changes = applet_change_service.compare(
        old_applet_history, new_applet_history
    )
    assert len(changes) == 1
    assert changes[0] == "Applet Description was changed to New"
