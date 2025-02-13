import uuid
from typing import Any

import pytest

from apps.activities.domain.activity_history import ActivityItemHistoryFull
from apps.activities.domain.conditional_logic import ConditionalLogic, Match
from apps.activities.domain.conditions import ConditionType, EqualCondition, ValuePayload
from apps.activities.domain.response_type_config import AdditionalResponseOption, ResponseType, SingleSelectionConfig
from apps.activities.domain.response_values import (
    SingleSelectionRowsValues,
    SingleSelectionValues,
    SliderRowsValue,
    SliderRowsValues,
    _SingleSelectionOption,
    _SingleSelectionRow,
    _SingleSelectionValue,
)
from apps.activities.services.activity_item_change import (
    ActivityItemChangeService,
    ConditionalLogicChangeService,
    ConfigChangeService,
    ResponseOptionChangeService,
)
from apps.shared.enums import Language

TEST_UUID = uuid.UUID("00000000-0000-0000-0000-000000000000")


@pytest.fixture
def old_version() -> str:
    return "1.0.0"


@pytest.fixture
def new_version() -> str:
    return "2.0.0"


@pytest.fixture
def item_change_service(old_version, new_version) -> ActivityItemChangeService:
    return ActivityItemChangeService(old_version, new_version)


@pytest.fixture
def old_id_version(old_version: str) -> str:
    return f"{TEST_UUID}_{old_version}"


@pytest.fixture
def new_id_version(new_version: str) -> str:
    return f"{TEST_UUID}_{new_version}"


@pytest.fixture
def single_selection_values() -> SingleSelectionValues:
    return SingleSelectionValues(
        palette_name=None,
        options=[
            _SingleSelectionValue(id=str(TEST_UUID), text="o1", value=0),
        ],
        type=ResponseType.SINGLESELECT,
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
        additional_response_option=AdditionalResponseOption(text_input_option=False, text_input_required=False),
        remove_back_button=False,
        set_palette=False,
        skippable_item=False,
        type=ResponseType.SINGLESELECT,
    )


@pytest.fixture
def slider_rows_values() -> SliderRowsValues:
    return SliderRowsValues(
        rows=[
            SliderRowsValue(
                id=str(TEST_UUID),
                label="TEST",
                min_label=None,
                max_label=None,
                min_value=0,
                max_value=5,
            )
        ],
        type=ResponseType.SLIDERROWS,
    )


@pytest.fixture
def single_select_rows_values() -> SingleSelectionRowsValues:
    return SingleSelectionRowsValues(
        rows=[_SingleSelectionRow(id=str(TEST_UUID), row_name="row1")],
        options=[_SingleSelectionOption(id=str(TEST_UUID), text="option 1")],
        type=ResponseType.SINGLESELECTROWS,
    )


@pytest.fixture
def conditional_logic() -> ConditionalLogic:
    return ConditionalLogic(
        conditions=[
            EqualCondition(
                item_name="test_item",
                type=ConditionType.EQUAL,
                payload=ValuePayload(value=1),
            )
        ]
    )


@pytest.fixture
def old_item(
    old_id_version: str,
    single_selection_values: SingleSelectionValues,
    single_selection_config: SingleSelectionConfig,
) -> ActivityItemHistoryFull:
    return ActivityItemHistoryFull(
        id=TEST_UUID,
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
def new_item(old_item: ActivityItemHistoryFull, new_id_version: str) -> ActivityItemHistoryFull:
    new_item = old_item.copy(deep=True)
    new_item.id_version = new_id_version
    new_item.activity_id = new_id_version
    return new_item


def test_initial_single_selection_values_change(
    single_selection_values: SingleSelectionValues,
) -> None:
    service = ResponseOptionChangeService()
    changes: list[str] = []
    service.check_changes(ResponseType.SINGLESELECT, single_selection_values, changes)
    assert changes == ["o1 | 0 option was added"]


def test_single_selection_values_update(
    single_selection_values: SingleSelectionValues,
) -> None:
    new_ssv = single_selection_values.copy(deep=True)
    new_text = "newoptionname"
    new_ssv.options[0].text = new_text
    changes: list[str] = []
    service = ResponseOptionChangeService()
    service.check_changes_update(ResponseType.SINGLESELECT, single_selection_values, new_ssv, changes)
    assert len(changes) == 1
    assert changes[0] == f"o1 | 0 option text was changed to {new_text} | 0"


def test_single_selection_remove_insert_with_the_same_name(
    single_selection_values: SingleSelectionValues,
) -> None:
    new_ssv = single_selection_values.copy(deep=True)
    new_ssv.options[0].id = str(uuid.uuid4())
    changes: list[str] = []
    service = ResponseOptionChangeService()
    service.check_changes_update(ResponseType.SINGLESELECT, single_selection_values, new_ssv, changes)
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
    service.check_changes_update(ResponseType.SINGLESELECT, single_selection_values, new_ssv, changes)
    assert changes == ["o2 | 0 option was added"]


def test_initial_slider_rows_values(
    slider_rows_values: SliderRowsValues,
) -> None:
    service = ResponseOptionChangeService()
    changes: list[str] = []
    service.check_changes(ResponseType.SLIDERROWS, slider_rows_values, changes)
    assert changes == [f"Row {slider_rows_values.rows[0].label} was added"]


def test_slider_rows_values_update(
    slider_rows_values: SliderRowsValues,
) -> None:
    new = slider_rows_values.copy(deep=True)
    old_label = slider_rows_values.rows[0].label
    new_label = "newlabel"
    new.rows[0].label = new_label
    changes: list[str] = []
    service = ResponseOptionChangeService()
    service.check_changes_update(ResponseType.SLIDERROWS, slider_rows_values, new, changes)
    assert len(changes) == 1
    assert changes[0] == f"Row label {old_label} was changed to {new_label}"


def test_slider_rows_values_added_new_row(
    slider_rows_values: SliderRowsValues,
) -> None:
    new = slider_rows_values.copy(deep=True)
    # Just copy for test new row one more time and change id
    new_row = new.rows[0].copy(deep=True)
    new_row.id = str(uuid.uuid4())
    new.rows.append(new_row)
    changes: list[str] = []
    service = ResponseOptionChangeService()
    service.check_changes_update(ResponseType.SLIDERROWS, slider_rows_values, new, changes)
    assert len(changes) == 1
    assert changes == [f"Row {new_row.label} was added"]


def test_slider_rows_values_removed_row(
    slider_rows_values: SliderRowsValues,
) -> None:
    new = slider_rows_values.copy(deep=True)
    new.rows = []
    label = slider_rows_values.rows[0].label
    changes: list[str] = []
    service = ResponseOptionChangeService()
    service.check_changes_update(ResponseType.SLIDERROWS, slider_rows_values, new, changes)
    assert len(changes) == 1
    assert changes == [f"Row {label} was removed"]


def test_initial_single_select_rows_values(
    single_select_rows_values: SingleSelectionRowsValues,
) -> None:
    service = ResponseOptionChangeService()
    changes: list[str] = []
    row_name = single_select_rows_values.rows[0].row_name
    option_text = single_select_rows_values.options[0].text
    service.check_changes(ResponseType.SINGLESELECTROWS, single_select_rows_values, changes)
    exp_changes = [
        f"Row {row_name} was added",
        f"{option_text} was added",
    ]
    assert changes == exp_changes


def test_single_select_rows_row_name_update(
    single_select_rows_values: SingleSelectionRowsValues,
) -> None:
    service = ResponseOptionChangeService()
    changes: list[str] = []
    old_name = single_select_rows_values.rows[0].row_name
    new = single_select_rows_values.copy(deep=True)
    new_name = "new row name"
    new.rows[0].row_name = new_name
    service.check_changes_update(ResponseType.SINGLESELECTROWS, single_select_rows_values, new, changes)
    assert changes == [f"Row name {old_name} was changed to {new_name}"]


def test_single_select_rows_option_text_update(
    single_select_rows_values: SingleSelectionRowsValues,
) -> None:
    service = ResponseOptionChangeService()
    changes: list[str] = []
    old_text = single_select_rows_values.options[0].text
    new = single_select_rows_values.copy(deep=True)
    new_text = "new"
    new.options[0].text = new_text
    service.check_changes_update(ResponseType.SINGLESELECTROWS, single_select_rows_values, new, changes)
    assert changes == [f"Option text {old_text} was changed to {new_text}"]


@pytest.mark.parametrize(
    "attr_name, exp_changes",
    (
        ("rows", ["Row row1 was added"]),
        ("options", ["option 1 option was added"]),
    ),
)
def test_single_select_rows_new_response_value_was_added(
    single_select_rows_values: SingleSelectionRowsValues,
    attr_name: str,
    exp_changes: list[str],
) -> None:
    service = ResponseOptionChangeService()
    changes: list[str] = []
    new = single_select_rows_values.copy(deep=True)
    # for test just copy and change id
    new_attr = getattr(new, attr_name)[0].copy(deep=True)
    new_attr.id = str(uuid.uuid4())
    getattr(new, attr_name).append(new_attr)
    service.check_changes_update(ResponseType.SINGLESELECTROWS, single_select_rows_values, new, changes)
    assert changes == exp_changes


# NOTE: For simple unit test for tracking changes we can avoid business logic
# that at least one row and one option is required.
@pytest.mark.parametrize(
    "attr_name, exp_changes",
    (
        ("rows", ["Row row1 was removed"]),
        ("options", ["option 1 option was removed"]),
    ),
)
def test_single_select_rows_new_response_value_was_removed(
    single_select_rows_values: SingleSelectionRowsValues,
    attr_name: str,
    exp_changes: list[str],
) -> None:
    service = ResponseOptionChangeService()
    changes: list[str] = []
    new = single_select_rows_values.copy(deep=True)
    setattr(new, attr_name, [])
    service.check_changes_update(ResponseType.SINGLESELECTROWS, single_select_rows_values, new, changes)
    assert changes == exp_changes


def test_conditional_logic_added(conditional_logic: ConditionalLogic):
    service = ConditionalLogicChangeService()
    changes: list[str] = []
    parent_name = ActivityItemChangeService.field_name_verbose_name_map["conditional_logic"]
    service.check_changes(parent_name, conditional_logic, changes)
    condition = conditional_logic.conditions[0]
    condition_type = condition.type.lower().replace("_", " ")
    item_name = condition.item_name
    value = condition.payload.value  # type: ignore
    assert changes == [f"{parent_name}: If All: {item_name} {condition_type} {value} was added"]


def test_conditional_logic_changed(conditional_logic: ConditionalLogic):
    service = ConditionalLogicChangeService()
    changes: list[str] = []
    parent_name = ActivityItemChangeService.field_name_verbose_name_map["conditional_logic"]
    new = conditional_logic.copy(deep=True)
    new.match = Match.ANY
    service.check_update_changes(parent_name, conditional_logic, new, changes)
    condition = conditional_logic.conditions[0]
    condition_type = condition.type.lower().replace("_", " ")
    item_name = condition.item_name
    value = condition.payload.value  # type: ignore
    assert changes == [f"{parent_name}: If {new.match.capitalize()}: {item_name} {condition_type} {value} was updated"]


def test_conditional_logic_removed(
    conditional_logic: ConditionalLogic,
) -> None:
    service = ConditionalLogicChangeService()
    changes: list[str] = []
    parent_name = ActivityItemChangeService.field_name_verbose_name_map["conditional_logic"]
    new = None
    service.check_update_changes(parent_name, conditional_logic, new, changes)
    assert changes == [f"{parent_name} was removed"]


def test_initial_single_selection_config_change(
    single_selection_config: SingleSelectionConfig,
) -> None:
    changes: list[str] = []
    service = ConfigChangeService()
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
        "Auto Advance was disabled",
    ]
    assert changes == exp_changes


def test_initial_single_selection_with_timer(
    single_selection_config: SingleSelectionConfig,
) -> None:
    timer = 99
    single_selection_config.timer = timer
    changes: list[str] = []
    service = ConfigChangeService()
    service.check_changes(single_selection_config, changes)
    assert f"Timer was set to {timer}" in changes


@pytest.mark.parametrize(
    "option, exp_change_msg",
    (
        ("text_input_option", "Add Text Input Option was enabled"),
        ("text_input_required", "Input Required was enabled"),
    ),
)
def test_initial_single_selection_additional_option_enabled(
    single_selection_config: SingleSelectionConfig,
    option: str,
    exp_change_msg: str,
) -> None:
    setattr(single_selection_config.additional_response_option, option, True)
    changes: list[str] = []
    service = ConfigChangeService()
    service.check_changes(single_selection_config, changes)
    assert exp_change_msg in changes


def test_single_selection_config_updated(
    single_selection_config: SingleSelectionConfig,
) -> None:
    new = single_selection_config.copy(deep=True)
    new.remove_back_button = True
    service = ConfigChangeService()
    changes: list[str] = []
    service.check_update_changes(single_selection_config, new, changes)
    assert changes == ["Remove Back Button was enabled"]


@pytest.mark.parametrize(
    "option, exp_change_msg",
    (
        ("text_input_option", "Add Text Input Option was enabled"),
        ("text_input_required", "Input Required was enabled"),
    ),
)
def test_single_selection_additional_option_enabled(
    single_selection_config: SingleSelectionConfig,
    option: str,
    exp_change_msg: str,
) -> None:
    new = single_selection_config.copy(deep=True)
    setattr(new.additional_response_option, option, True)
    changes: list[str] = []
    service = ConfigChangeService()
    service.check_update_changes(single_selection_config, new, changes)
    assert exp_change_msg in changes


def test_single_selection_config_timer_was_added(
    single_selection_config: SingleSelectionConfig,
) -> None:
    timer = 99
    new = single_selection_config.copy(deep=True)
    new.timer = timer
    changes: list[str] = []
    service = ConfigChangeService()
    service.check_update_changes(single_selection_config, new, changes)
    assert [f"Timer was set to {timer}"] == changes


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
        "Auto Advance was disabled",
    ]
    changes = item_change_service.get_changes_insert(new_item)
    assert changes == single_select_exp_changes


def test_no_changes_in_versions(
    old_item: ActivityItemHistoryFull,
    new_item: ActivityItemHistoryFull,
    item_change_service: ActivityItemChangeService,
) -> None:
    changes = item_change_service.get_changes_update(old_item, new_item)
    assert not changes


def test_initial_item_is_hidden_true(
    new_item: ActivityItemHistoryFull,
    item_change_service: ActivityItemChangeService,
) -> None:
    new_item.is_hidden = True
    changes = item_change_service.get_changes_insert(new_item)
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
    changes = item_change_service.get_changes_update(old_item, new_item)
    assert len(changes) == 1
    assert changes[0] == exp_change_msg


@pytest.mark.parametrize("exp_change_msg", ("Item test_item was removed",))
def test_item_removed(
    old_item: ActivityItemHistoryFull,
    item_change_service: ActivityItemChangeService,
    exp_change_msg: str,
) -> None:
    changes = item_change_service.get_changes([old_item])
    assert len(changes) == 1
    assert changes[0].name == exp_change_msg
