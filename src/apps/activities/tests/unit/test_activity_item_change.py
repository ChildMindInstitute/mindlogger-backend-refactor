import uuid
from typing import Any

import pytest

from apps.activities.domain.activity_history import ActivityItemHistoryFull
from apps.activities.domain.response_type_config import (
    AdditionalResponseOption,
    ResponseType,
    SingleSelectionConfig,
)
from apps.activities.domain.response_values import (
    SingleSelectionValues,
    _SingleSelectionValue,
)
from apps.activities.services.activity_item_change import (
    ActivityItemChangeService,
    ConfigChangeService,
    ResponseOptionChangeService,
)
from apps.shared.enums import Language


@pytest.fixture
def item_id() -> uuid.UUID:
    return uuid.UUID("00000000-0000-0000-0000-000000000000")


@pytest.fixture
def old_version() -> str:
    return "1.0.0"


@pytest.fixture
def new_version() -> str:
    return "2.0.0"


@pytest.fixture
def old_id_version(item_id: uuid.UUID, old_version: str) -> str:
    return f"{item_id}_{old_version}"


@pytest.fixture
def new_id_version(item_id: uuid.UUID, new_version: str) -> str:
    return f"{item_id}_{new_version}"


@pytest.fixture
def single_selection_values() -> SingleSelectionValues:
    return SingleSelectionValues(
        palette_name=None,
        options=[
            _SingleSelectionValue(
                id=str(uuid.UUID("00000000-0000-0000-0000-000000000000")),
                text="o1",
                image=None,
                score=None,
                tooltip=None,
                color=None,
                alert=None,
                value=0,
            ),
        ],
    )


@pytest.fixture
def single_selection_config() -> SingleSelectionConfig:
    return SingleSelectionConfig(
        randomize_options=False,
        timer=0,
        add_scores=False,
        set_alerts=False,
        add_tooltip=False,
        add_tokens=False,
        additional_response_option=AdditionalResponseOption(
            text_input_option=False, text_input_required=False
        ),
        remove_back_button=False,
        set_palette=False,
        skippable_item=False,
    )


@pytest.fixture
def old_item(
    item_id: uuid.UUID,
    old_id_version: str,
    single_selection_values: SingleSelectionValues,
    single_selection_config: SingleSelectionConfig,
) -> ActivityItemHistoryFull:
    return ActivityItemHistoryFull(
        id=item_id,
        id_version=old_id_version,
        activity_id=old_id_version,
        order=1,
        question={Language.ENGLISH: "Question"},
        response_type=ResponseType.SINGLESELECT,
        response_values=single_selection_values,
        config=single_selection_config,
        name="test_item",
        is_hidden=False,
        allow_edit=False,
    )


@pytest.fixture
def new_item(
    old_item: ActivityItemHistoryFull, new_id_version: str
) -> ActivityItemHistoryFull:
    new_item = old_item.copy(deep=True)
    new_item.id_version = new_id_version
    new_item.activity_id = new_id_version
    return new_item


@pytest.fixture
def item_change_service() -> ActivityItemChangeService:
    return ActivityItemChangeService()


def test_initial_single_selection_values_change(
    single_selection_values: SingleSelectionValues,
) -> None:
    service = ResponseOptionChangeService()
    changes: list[str] = []
    service.check_changes(
        ResponseType.SINGLESELECT, single_selection_values, changes
    )
    assert changes == ["o1 | 0 option was added"]


def test_single_selection_values_update(
    single_selection_values: SingleSelectionValues,
) -> None:
    new_ssv = single_selection_values.copy(deep=True)
    new_text = "newoptionname"
    new_ssv.options[0].text = new_text
    changes: list[str] = []
    service = ResponseOptionChangeService()
    service.check_changes_update(
        ResponseType.SINGLESELECT, single_selection_values, new_ssv, changes
    )
    assert len(changes) == 1
    assert changes[0] == f"o1 | 0 option name was changed to {new_text} | 0"


def test_single_selection_remove_insert_with_the_same_name(
    single_selection_values: SingleSelectionValues,
) -> None:
    new_ssv = single_selection_values.copy(deep=True)
    new_ssv.options[0].id = str(uuid.uuid4())
    changes: list[str] = []
    service = ResponseOptionChangeService()
    service.check_changes_update(
        ResponseType.SINGLESELECT, single_selection_values, new_ssv, changes
    )
    exp_changes = ["o1 | 0 option was removed", "o1 | 0 option was added"]
    assert changes == exp_changes


def test_single_selection_added_new_option(
    single_selection_values: SingleSelectionValues,
) -> None:
    new_ssv = single_selection_values.copy(deep=True)
    op = new_ssv.options[0].copy(deep=True)
    op.id = str(uuid.uuid4())
    op.text = "o2"
    new_ssv.options.append(op)
    changes: list[str] = []
    service = ResponseOptionChangeService()
    service.check_changes_update(
        ResponseType.SINGLESELECT, single_selection_values, new_ssv, changes
    )
    assert changes == ["o2 | 0 option was added"]


def test_initial_single_selection_config_change(
    single_selection_config: SingleSelectionConfig,
) -> None:
    service = ConfigChangeService()
    changes: list[str] = []
    service.check_changes(single_selection_config, changes)
    exp_changes = [
        "Remove Back Button was disabled",
        "Skippable Item was disabled",
        "Randomize Options was disabled",
        "Add Scores was disabled",
        "Set Alerts was disabled",
        "Add Tooltips was disabled",
        "Set Color Palette was disabled",
        "Tokens was disabled",
        "Add Text Input Option was disabled",
        "Input Required was disabled",
    ]
    assert changes == exp_changes


def test_initial_single_selection_with_timer(
    single_selection_config: SingleSelectionConfig,
) -> None:
    service = ConfigChangeService()
    timer = 99
    single_selection_config.timer = timer
    changes: list[str] = []
    service.check_changes(single_selection_config, changes)
    assert f"Timer was set to {timer}" in changes


def test_initial_version_changes(
    new_item: ActivityItemHistoryFull,
    item_change_service: ActivityItemChangeService,
) -> None:
    # NOTE: for another response types initial changes can be different
    single_select_exp_changes = [
        "Item Name was set to test_item",
        "Displayed Content was set to Question",
        "Item Type was set to singleSelect",
        "o1 | 0 option was added",
        "Item Order was set to 1",
        "Item Visibility was enabled",
        "Remove Back Button was disabled",
        "Skippable Item was disabled",
        "Randomize Options was disabled",
        "Add Scores was disabled",
        "Set Alerts was disabled",
        "Add Tooltips was disabled",
        "Set Color Palette was disabled",
        "Tokens was disabled",
        "Add Text Input Option was disabled",
        "Input Required was disabled",
    ]
    changes = item_change_service.generate_activity_items_insert(new_item)
    assert changes == single_select_exp_changes


def test_no_changes_in_versions(
    old_item: ActivityItemHistoryFull,
    new_item: ActivityItemHistoryFull,
    item_change_service: ActivityItemChangeService,
) -> None:
    changes = item_change_service.compare_items(old_item, new_item)
    assert not changes


def test_initial_item_is_hidden_true(
    new_item: ActivityItemHistoryFull,
    item_change_service: ActivityItemChangeService,
) -> None:
    new_item.is_hidden = True
    changes = item_change_service.generate_activity_items_insert(new_item)
    assert "Item Visibility was disabled" in changes


@pytest.mark.parametrize(
    "field, value, exp_change_msg",
    (
        (
            "question",
            {Language.ENGLISH: "New Question"},
            "Displayed Content was changed to New Question",
        ),
        (
            "is_hidden",
            True,
            "Item Visibility was disabled",
        ),
        ("order", 2, "Item Order was changed to 2"),
        ("name", "new name", "Item Name was changed to newname"),
    ),
)
def test_field_changed(
    old_item: ActivityItemHistoryFull,
    new_item: ActivityItemHistoryFull,
    item_change_service: ActivityItemChangeService,
    field: str,
    value: Any,
    exp_change_msg: str,
) -> None:
    setattr(new_item, field, value)
    changes = item_change_service.compare_items(old_item, new_item)
    assert len(changes) == 1
    assert changes[0] == exp_change_msg
