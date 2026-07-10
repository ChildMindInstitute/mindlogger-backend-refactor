"""Unit tests for the audit module.

These are pure-Python tests that don't need DB / HTTP fixtures, so they
don't inherit from `BaseTest` and don't need pytest fixtures.
"""

import pytest

from apps.audit.constants import (
    ACCOUNT_LEVEL_EXPORT_ACTIONS,
    EVENT_ACTION_TO_EVENT_CATEGORY,
    EVENT_ACTION_TO_EVENT_TYPE,
)
from apps.audit.enums import EventAction


@pytest.mark.parametrize(
    "constant_name,constant",
    [
        ("EVENT_ACTION_TO_EVENT_CATEGORY", EVENT_ACTION_TO_EVENT_CATEGORY),
        ("EVENT_ACTION_TO_EVENT_TYPE", EVENT_ACTION_TO_EVENT_TYPE),
    ],
)
def test_constant_covers_all_event_actions(constant_name: str, constant: dict) -> None:
    """Every `EventAction` member must have an entry in the lookup constant.

    Guards against forgetting to add a new action's mapping when extending
    the `EventAction` enum.
    """
    missing = set(EventAction) - set(constant)
    extra = set(constant) - set(EventAction)
    assert not missing, f"{constant_name} is missing entries for: {sorted(m.value for m in missing)}"
    assert not extra, f"{constant_name} has extra entries not in EventAction: {extra}"


def test_account_level_export_actions() -> None:
    """The account-level export set carries all ``user:*`` actions.

    Guards the export scoping policy: applet-scoped actions must never be
    classified as account-level.
    """
    expected = {action for action in EventAction if action.resource == "user"}
    assert ACCOUNT_LEVEL_EXPORT_ACTIONS == expected
    # All account-level actions are applet-less (their resource is "user", never "applet").
    assert all(action.resource == "user" for action in ACCOUNT_LEVEL_EXPORT_ACTIONS)
