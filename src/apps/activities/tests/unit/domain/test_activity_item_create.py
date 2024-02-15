import uuid
from typing import cast

import pytest

from apps.activities import errors
from apps.activities.domain.activity_create import ActivityItemCreate
from apps.activities.domain.response_type_config import DrawingConfig, ResponseType, TextConfig
from apps.activities.domain.response_values import (
    DrawingValues,
    MultiSelectionValues,
    NumberSelectionValues,
    SingleSelectionRowsValues,
    SingleSelectionValues,
    _MultiSelectionValue,
)
from apps.activities.tests.utils import BaseItemData
from apps.shared.domain.custom_validations import InvalidImageError


def test_create_activity_item_conditional_logic_not_valid_response_type_config(
    base_item_data, date_config, conditional_logic
) -> None:
    with pytest.raises(errors.IncorrectConditionLogicItemTypeError):
        ActivityItemCreate(
            **base_item_data.dict(),
            config=date_config,
            response_type=ResponseType.DATE,
            conditional_logic=conditional_logic,
            response_values=None,
        )


def test_create_activity_item_conditional_logic_can_not_be_hidden(
    base_item_data,
    single_select_config,
    conditional_logic,
    single_select_response_values,
) -> None:
    base_item_data.is_hidden = True
    with pytest.raises(errors.HiddenWhenConditionalLogicSetError):
        ActivityItemCreate(
            **base_item_data.dict(),
            config=single_select_config,
            conditional_logic=conditional_logic,
            response_values=single_select_response_values,
            response_type=ResponseType.SINGLESELECT,
        )


def test_create_activity_item_slider_alerts_provided_but_set_alerts_not_set(slider_item_create, slider_value_alert):
    data = slider_item_create.dict()
    data["response_values"]["alerts"] = [slider_value_alert.dict()]
    data["config"]["set_alerts"] = False
    with pytest.raises(errors.AlertFlagMissingSliderItemError):
        ActivityItemCreate(**data)


def test_create_activity_item_slider_alerts_not_valid_alert_value(slider_item_create, slider_value_alert):
    data = slider_item_create.dict()
    alert_data = slider_value_alert.dict()
    alert_data["value"] = None
    data["response_values"]["alerts"] = [alert_data]
    data["config"]["set_alerts"] = True
    with pytest.raises(errors.SliderMinMaxValueError):
        ActivityItemCreate(**data)


@pytest.mark.parametrize("min_value,max_value", ((1, None), (None, 1)))
def test_create_activity_item_slider_alerts_not_valid_alert_min_max_values(
    slider_item_create, slider_value_alert, min_value, max_value
):
    data = slider_item_create.dict()
    alert_data = slider_value_alert.dict()
    alert_data["min_value"] = min_value
    alert_data["max_value"] = max_value
    data["response_values"]["alerts"] = [alert_data]
    data["config"]["set_alerts"] = True
    data["config"]["continuous_slider"] = True
    with pytest.raises(errors.SliderMinMaxValueError):
        ActivityItemCreate(**data)


def test_create_activity_item_slider_alerts_min_value_greater_then_max_value(slider_item_create, slider_value_alert):
    data = slider_item_create.dict()
    alert_data = slider_value_alert.dict()
    alert_data["min_value"] = 10
    alert_data["max_value"] = 0
    data["response_values"]["alerts"] = [alert_data]
    data["config"]["set_alerts"] = True
    data["config"]["continuous_slider"] = True
    with pytest.raises(errors.MinValueError):
        ActivityItemCreate(**data)


def test_create_activity_item_slider_min_value_greater_then_max_value(
    slider_item_create,
):
    data = slider_item_create.dict()
    data["response_values"]["min_value"] = 10
    data["response_values"]["max_value"] = 0
    with pytest.raises(errors.MinValueError):
        ActivityItemCreate(**data)


def test_create_activity_item_slider_rows_with_alerts_value_is_none(slider_rows_item_create, slider_value_alert):
    slider_value_alert.value = None
    alert_data = slider_value_alert.dict()
    data = slider_rows_item_create.dict()
    data["response_values"]["rows"][0]["alerts"] = [alert_data]
    with pytest.raises(errors.SliderRowsValueError):
        ActivityItemCreate(**data)


def test_create_activity_item_slider_rows_with_alerts_value_is_not_none_but_alerts_not_set(  # noqa: E501
    slider_rows_item_create, slider_value_alert
):
    alert_data = slider_value_alert.dict()
    slider_rows_item_create.config.set_alerts = False
    data = slider_rows_item_create.dict()
    data["response_values"]["rows"][0]["alerts"] = [alert_data]
    with pytest.raises(errors.AlertFlagMissingSliderItemError):
        ActivityItemCreate(**data)


@pytest.mark.parametrize("fixture_name,", ("single_select_item_create", "multi_select_item_create"))
def test_create_activity_item_single_multi_select_alert_is_not_none_but_set_alerts_not_set(  # noqa: E501
    request,
    fixture_name,
) -> None:
    fixture = request.getfixturevalue(fixture_name)
    data = fixture.dict()
    data["config"]["set_alerts"] = False
    data["response_values"]["options"][0]["alert"] = "alert"
    with pytest.raises(errors.AlertFlagMissingSingleMultiRowItemError):
        ActivityItemCreate(**data)


@pytest.mark.parametrize(
    "fixture_name,",
    ("single_select_row_item_create", "multi_select_row_item_create"),
)
def test_create_activity_item_single_multi_select_row_alert_is_not_none_but_set_alerts_not_set(  # noqa: E501
    request,
    fixture_name,
) -> None:
    fixture = request.getfixturevalue(fixture_name)
    data = fixture.dict()
    data["config"]["set_alerts"] = False
    data["response_values"]["data_matrix"][0]["options"][0]["alert"] = "alert"
    with pytest.raises(errors.AlertFlagMissingSingleMultiRowItemError):
        ActivityItemCreate(**data)


def test_single_select_row_response_values_not_valid_data_matrix_len_does_not_equal_len_rows(  # noqa: E501
    single_select_row_response_values: SingleSelectionRowsValues,
):
    data = single_select_row_response_values.dict()
    data["data_matrix"] = []
    with pytest.raises(errors.InvalidDataMatrixError):
        SingleSelectionRowsValues(**data)


def test_single_select_row_response_values_not_valid_data_matrix_len_options_does_not_equal_len_per_row(  # noqa: E501
    single_select_row_response_values: SingleSelectionRowsValues,
):
    data = single_select_row_response_values.dict()
    data["data_matrix"][0]["options"] = []
    with pytest.raises(errors.InvalidDataMatrixByOptionError):
        SingleSelectionRowsValues(**data)


def test_number_selection_response_values_min_value_greater_than_max_value(
    number_select_response_values,
):
    data = number_select_response_values.dict()
    data["min_value"], data["max_value"] = data["max_value"], data["min_value"]
    with pytest.raises(errors.MinValueError):
        NumberSelectionValues(**data)


def test_number_selection_response_values_min_value_is_equal_max_value(
    number_select_response_values,
):
    data = number_select_response_values.dict()
    data["min_value"], data["max_value"] = 0, 0
    with pytest.raises(errors.MinValueError):
        NumberSelectionValues(**data)


@pytest.mark.parametrize(
    "field_name,value",
    (
        ("drawing_example", "notfile"),
        ("drawing_example", "badextenstion.xxx"),
        ("drawing_background", "notfile"),
        ("drawing_background", "badextenstion.xxx"),
    ),
)
def test_drawing_response_values_image_name_does_not_start_with_http(
    drawing_response_values: DrawingValues, field_name: str, value: str
):
    data = drawing_response_values.dict()
    data[field_name] = value
    with pytest.raises(InvalidImageError):
        DrawingValues(**data)


def test_create_item_with_drawing_response_values(
    drawing_response_values: DrawingValues,
    drawing_config: DrawingConfig,
    base_item_data: BaseItemData,
    remote_image: str,
):
    item = ActivityItemCreate(
        response_type=ResponseType.DRAWING,
        config=drawing_config,
        response_values=drawing_response_values,
        **base_item_data.dict(),
    )
    item.response_values = cast(DrawingValues, item.response_values)
    assert item.response_values.drawing_background == remote_image
    assert item.response_values.drawing_example == remote_image


def test_create_item_with_drawing_response_values_images_are_none(
    drawing_config: DrawingConfig,
    base_item_data: BaseItemData,
):
    item = ActivityItemCreate(
        response_type=ResponseType.DRAWING,
        config=drawing_config,
        response_values=DrawingValues(drawing_background=None, drawing_example=None),
        **base_item_data.dict(),
    )
    item.response_values = cast(DrawingValues, item.response_values)
    assert item.response_values.drawing_background is None
    assert item.response_values.drawing_example is None


def test_create_item_single_select_row_option_with_image(
    single_select_row_item_create: ActivityItemCreate, remote_image: str
):
    single_select_row_item_create.response_values = cast(
        SingleSelectionRowsValues,
        single_select_row_item_create.response_values,
    )
    single_select_row_item_create.response_values.options[0].image = remote_image
    data = single_select_row_item_create.dict()
    item = ActivityItemCreate(**data)
    item.response_values = cast(SingleSelectionRowsValues, item.response_values)
    assert item.response_values.options[0].image == remote_image


def test_create_item_single_select_row_row_with_image(
    single_select_row_item_create: ActivityItemCreate, remote_image: str
):
    single_select_row_item_create.response_values = cast(
        SingleSelectionRowsValues,
        single_select_row_item_create.response_values,
    )
    single_select_row_item_create.response_values.rows[0].row_image = remote_image
    data = single_select_row_item_create.dict()
    item = ActivityItemCreate(**data)
    item.response_values = cast(SingleSelectionRowsValues, item.response_values)
    assert item.response_values.rows[0].row_image == remote_image


def test_text_item_config_correct_anser_required(
    text_config: TextConfig,
):
    data = text_config.dict()
    data["correct_answer"] = None
    data["correct_answer_required"] = True
    with pytest.raises(errors.CorrectAnswerRequiredError):
        TextConfig(**data)


def test_activity_item_create_response_values_not_none_for_non_response_response_type(  # noqa: E501
    text_item_create: ActivityItemCreate,
    single_select_response_values: SingleSelectionValues,
):
    data = text_item_create.dict()
    data["response_values"] = single_select_response_values.dict()
    with pytest.raises(errors.IncorrectResponseValueError):
        ActivityItemCreate(**data)


def test_multi_select_response_values_multiple_none_options(  # noqa: E501
    multi_select_reponse_values: MultiSelectionValues,
):
    data = multi_select_reponse_values.dict()
    data["options"].append(
        _MultiSelectionValue(
            id=str(uuid.uuid4()),
            text="text1",
            image=None,
            score=None,
            tooltip=None,
            is_hidden=False,
            color=None,
            value=0,
            is_none_above=True,
        )
    )
    data["options"].append(
        _MultiSelectionValue(
            id=str(uuid.uuid4()),
            text="text2",
            image=None,
            score=None,
            tooltip=None,
            is_hidden=False,
            color=None,
            value=0,
            is_none_above=True,
        )
    )

    with pytest.raises(errors.MultiSelectNoneOptionError):
        MultiSelectionValues(**data)
