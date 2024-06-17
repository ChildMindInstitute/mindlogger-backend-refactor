import uuid
from typing import cast

import pytest

from apps.activities import errors
from apps.activities.domain.activity_create import ActivityItemCreate
from apps.activities.domain.response_type_config import (
    DateConfig,
    DrawingConfig,
    ResponseType,
    SingleSelectionConfig,
    SliderConfig,
    SliderRowsConfig,
    TextConfig,
)
from apps.activities.domain.response_values import (
    DrawingValues,
    MultiSelectionValues,
    NumberSelectionValues,
    SingleSelectionRowsValues,
    SingleSelectionValues,
    SliderRowsValues,
    SliderValues,
    _MultiSelectionValue,
)
from apps.activities.tests.utils import BaseItemData
from apps.shared.domain.custom_validations import InvalidImageError


def test_create_activity_item_conditional_logic_not_valid_response_type_config(
    base_item_data, photo_config, conditional_logic_equal
) -> None:
    with pytest.raises(errors.IncorrectConditionLogicItemTypeError):
        ActivityItemCreate(
            **base_item_data.dict(),
            config=photo_config,
            response_type=ResponseType.PHOTO,
            conditional_logic=conditional_logic_equal,
            response_values=None,
        )


def test_create_activity_item_conditional_logic_can_not_be_hidden(
    base_item_data,
    single_select_config,
    conditional_logic_equal,
    single_select_response_values,
) -> None:
    base_item_data.is_hidden = True
    with pytest.raises(errors.HiddenWhenConditionalLogicSetError):
        ActivityItemCreate(
            **base_item_data.dict(),
            config=single_select_config,
            conditional_logic=conditional_logic_equal,
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
    number_selection_response_values,
):
    data = number_selection_response_values.dict()
    data["min_value"], data["max_value"] = data["max_value"], data["min_value"]
    with pytest.raises(errors.MinValueError):
        NumberSelectionValues(**data)


def test_number_selection_response_values_min_value_is_equal_max_value(
    number_selection_response_values,
):
    data = number_selection_response_values.dict()
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


@pytest.mark.parametrize(
    "proportion",
    [
        "N/A",
        None,
        dict(enabled=False),
    ],
)
def test_create_item_with_drawing_response_values_proportion_from_json(
    drawing_response_values: DrawingValues,
    drawing_config: DrawingConfig,
    base_item_data: BaseItemData,
    proportion: dict | str | None,
):
    data = ActivityItemCreate(
        response_type=ResponseType.DRAWING,
        config=drawing_config,
        response_values=drawing_response_values,
        **base_item_data.dict(),
    ).dict()

    del data["response_values"]["proportion"]
    if proportion != "N/A":
        data["response_values"]["proportion"] = proportion

    item = ActivityItemCreate(**data)

    item.response_values = cast(DrawingValues, item.response_values)
    if proportion != "N/A":
        assert "proportion" in data["response_values"]
        if isinstance(proportion, dict):
            assert item.response_values.proportion.dict() == proportion  # type: ignore[union-attr]
        else:
            assert item.response_values.proportion == proportion
    else:
        assert "proportion" not in data["response_values"]
        assert item.response_values.proportion is None


def test_create_item_with_drawing_response_values_images_are_none(
    drawing_config: DrawingConfig,
    base_item_data: BaseItemData,
):
    item = ActivityItemCreate(
        response_type=ResponseType.DRAWING,
        config=drawing_config,
        response_values=DrawingValues(drawing_background=None, drawing_example=None, type=ResponseType.DRAWING),
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
    multi_select_response_values: MultiSelectionValues,
):
    data = multi_select_response_values.dict()
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


def test_create_item__item_name_with_not_valid_character(base_item_data: BaseItemData, date_config: DateConfig):
    name = "%_percent_not_allowed"
    with pytest.raises(errors.IncorrectNameCharactersError):
        ActivityItemCreate(
            question=base_item_data.question,
            name=name,
            config=date_config,
            response_type=ResponseType.DATE,
            response_values=None,
        )


@pytest.mark.parametrize("field_to_delete", ("add_scores", "set_alerts"))
def test_create_item__not_valid_config_missing_add_scores_and_set_alerts(
    single_select_item_create, field_to_delete
) -> None:
    data = single_select_item_create.dict()
    del data["config"][field_to_delete]
    with pytest.raises(errors.IncorrectConfigError) as exc:
        ActivityItemCreate(**data)
    assert exc.value.message.format(type=SingleSelectionConfig)


@pytest.mark.parametrize("response_type", (None, "NotValid"))
def test_create_item__not_valid_response_type(single_select_item_create, response_type) -> None:
    data = single_select_item_create.dict()
    data["response_type"] = response_type
    with pytest.raises(errors.IncorrectResponseValueError) as exc:
        ActivityItemCreate(**data)
    assert exc.value.message.format(type=ResponseType)


@pytest.mark.parametrize("value", (None, {}))
def test_create_single_select_item__not_valid_response_values(single_select_item_create, value):
    data = single_select_item_create.dict()
    data["response_values"] = value
    with pytest.raises(errors.IncorrectResponseValueError) as exc:
        ActivityItemCreate(**data)
    assert exc.value.message.format(type=SingleSelectionValues)


def test_create_item__reponse_type_absent(single_select_item_create) -> None:
    data = single_select_item_create.dict()
    del data["response_type"]
    with pytest.raises(ValueError):
        ActivityItemCreate(**data)


@pytest.mark.parametrize("fixture_name", ("single_select_item_create", "multi_select_item_create"))
def test_create_single_multi_select_item__add_scores_is_true_without_scores(request, fixture_name):
    fixture = request.getfixturevalue(fixture_name)
    data = fixture.dict()
    data["config"]["add_scores"] = True
    with pytest.raises(errors.ScoreRequiredForResponseValueError):
        ActivityItemCreate(**data)


def test_create_slider_item__add_scores_is_true_without_scores(slider_item_create):
    data = slider_item_create.dict()
    data["config"]["add_scores"] = True
    with pytest.raises(errors.NullScoreError):
        ActivityItemCreate(**data)


def test_create_slider_item__add_scores__scores_not_for_all_values(slider_item_create):
    data = slider_item_create.dict()
    min_val = slider_item_create.response_values.min_value
    max_val = slider_item_create.response_values.max_value
    scores = [i for i in range(max_val - min_val)]
    data["config"]["add_scores"] = True
    data["response_values"]["scores"] = scores
    with pytest.raises(errors.InvalidScoreLengthError):
        ActivityItemCreate(**data)


def test_create_slider_rows_item__add_scores_is_true__no_scores(slider_rows_item_create):
    data = slider_rows_item_create.dict()
    data["config"]["add_scores"] = True
    data["response_values"]["rows"][0]["scores"] = None
    with pytest.raises(errors.NullScoreError):
        ActivityItemCreate(**data)


def test_create_slider_rows_item__add_scores__scores_not_for_all_values(slider_rows_item_create):
    data = slider_rows_item_create.dict()
    min_val = slider_rows_item_create.response_values.rows[0].min_value
    max_val = slider_rows_item_create.response_values.rows[0].max_value
    scores = [i for i in range(max_val - min_val)]
    data["config"]["add_scores"] = True
    data["response_values"]["rows"][0]["scores"] = scores
    with pytest.raises(errors.InvalidScoreLengthError):
        ActivityItemCreate(**data)


@pytest.mark.parametrize(
    "fixture_name,field",
    (
        ("single_select_row_item_create", "set_alerts"),
        ("single_select_row_item_create", "add_scores"),
        ("multi_select_row_item_create", "set_alerts"),
        ("multi_select_row_item_create", "add_scores"),
    ),
)
def test_create_single_multi_select_row_item_no_datamatrix(request, fixture_name, field):
    fixture = request.getfixturevalue(fixture_name)
    data = fixture.dict()
    data["config"][field] = True
    data["response_values"]["data_matrix"] = None
    with pytest.raises(errors.DataMatrixRequiredError):
        ActivityItemCreate(**data)


def test_create_slider_rows_item_with_scores(slider_rows_item_create: ActivityItemCreate):
    slider_rows_item_create.response_values = cast(SliderRowsValues, slider_rows_item_create.response_values)
    slider_rows_item_create.config = cast(SliderRowsConfig, slider_rows_item_create.config)
    min_val = slider_rows_item_create.response_values.rows[0].min_value
    max_val = slider_rows_item_create.response_values.rows[0].max_value
    slider_rows_item_create.response_values.rows[0].scores = [i for i in range(max_val - min_val + 1)]
    slider_rows_item_create.config.add_scores = True
    item = ActivityItemCreate(**slider_rows_item_create.dict())
    item.config = cast(SliderRowsConfig, item.config)
    item.response_values = cast(SliderRowsValues, item.response_values)
    assert item.config.add_scores
    assert item.response_values.rows[0].scores == slider_rows_item_create.response_values.rows[0].scores


@pytest.mark.parametrize("fixture_name", ("single_select_row_item_create", "multi_select_row_item_create"))
def test_create_single_multi_select_row_item_add_alerts(request, fixture_name):
    fixture = request.getfixturevalue(fixture_name)
    data = fixture.dict()
    data["config"]["set_alerts"] = True
    item = ActivityItemCreate(**data)
    assert item.config.set_alerts


def test_slider_item_with_alert(
    base_item_data: BaseItemData, slider_value_alert, slider_response_values, slider_config
):
    slider_config.set_alerts = True
    slider_response_values.alerts = [slider_value_alert]
    item = ActivityItemCreate(
        **base_item_data.dict(),
        config=slider_config,
        response_values=slider_response_values,
        response_type=ResponseType.SLIDER,
    )
    item.config = cast(SliderConfig, item.config)
    item.response_values = cast(SliderValues, item.response_values)
    assert item.config.set_alerts
    assert isinstance(item.response_values.alerts, list)
    assert len(item.response_values.alerts) == 1
    assert item.response_values.alerts[0] == slider_value_alert


def test_slider_item__continuous_slider_with_alert(
    base_item_data: BaseItemData, slider_value_alert, slider_response_values, slider_config
):
    slider_config.set_alerts = True
    slider_config.continuous_slider = True
    slider_value_alert.min_value = slider_response_values.min_value
    slider_value_alert.max_value = slider_response_values.max_value
    slider_response_values.alerts = [slider_value_alert]
    item = ActivityItemCreate(
        **base_item_data.dict(),
        config=slider_config,
        response_values=slider_response_values,
        response_type=ResponseType.SLIDER,
    )
    item.config = cast(SliderConfig, item.config)
    item.response_values = cast(SliderValues, item.response_values)
    assert item.config.set_alerts
    assert isinstance(item.response_values.alerts, list)
    assert len(item.response_values.alerts) == 1
    assert item.response_values.alerts[0] == slider_value_alert


def test_slider_rows_item_with_alert(
    base_item_data: BaseItemData, slider_rows_response_values, slider_rows_config, slider_value_alert
):
    slider_rows_config.set_alerts = True
    slider_rows_response_values.rows[0].alerts = [slider_value_alert]
    item = ActivityItemCreate(
        **base_item_data.dict(),
        config=slider_rows_config,
        response_values=slider_rows_response_values,
        response_type=ResponseType.SLIDERROWS,
    )
    item.config = cast(SliderRowsConfig, item.config)
    item.response_values = cast(SliderRowsValues, item.response_values)
    assert item.config.set_alerts
    assert isinstance(item.response_values.rows[0].alerts, list)
    assert item.response_values.rows[0].alerts[0] == slider_value_alert


@pytest.mark.parametrize("fixture_name", ("single_select_row_item_create", "multi_select_row_item_create"))
def test_single_multi_select_item_row_without_datamatrix(request, fixture_name: str):
    fixture = request.getfixturevalue(fixture_name)
    data = fixture.dict()
    data["response_values"].pop("data_matrix", None)
    item = ActivityItemCreate(**data)
    assert item.response_values.data_matrix is None  # type: ignore[union-attr]


@pytest.mark.parametrize("fixture_name", ("single_select_row_item_create", "multi_select_row_item_create"))
def test_single_multi_select_item_row__option_value_is_none(request, fixture_name: str):
    fixture = request.getfixturevalue(fixture_name)
    data = fixture.dict()
    data["response_values"]["options"][0]["value"] = None
    item = ActivityItemCreate(**data)
    assert item.response_values.data_matrix[0].options[0].value == 0  # type: ignore


@pytest.mark.parametrize("fixture_name", ("single_select_item_create", "multi_select_item_create"))
def test_create_single_multi_select_item__add_scores_is_true_with_scores_float_rounded(request, fixture_name):
    fixture = request.getfixturevalue(fixture_name)
    data = fixture.dict()
    data["config"]["add_scores"] = True
    data["response_values"]["options"][0]["score"] = 1.333
    item = ActivityItemCreate(**data)
    assert item.response_values.options[0].score == round(data["response_values"]["options"][0]["score"], 2)


def test_create_slider_item__add_scores_is_true_with_scores_float_rounded(slider_item_create):
    data = slider_item_create.dict()
    data["config"]["add_scores"] = True
    data["response_values"]["scores"] = [
        i + 0.343 for i in range(data["response_values"]["max_value"] - data["response_values"]["min_value"] + 1)
    ]
    item = ActivityItemCreate(**data)
    rounded_score = [round(i, 2) for i in data["response_values"]["scores"]]

    for score in item.response_values.scores:
        assert score in rounded_score


def test_create_message_item__sanitize_question(message_item_create):
    data = message_item_create.dict()
    data["question"] = {"en": "One <script>alert('test')</script> Two"}
    item = ActivityItemCreate(**data)
    assert item.question["en"] == "One  Two"


@pytest.mark.parametrize(
    "response_type, config_fixture, cnd_logic_fixture, response_values_fixture",
    (
        (ResponseType.SINGLESELECT, "single_select_config", "conditional_logic_equal", "single_select_response_values"),
        (ResponseType.MULTISELECT, "multi_select_config", "conditional_logic_equal", "multi_select_response_values"),
        (ResponseType.SLIDER, "slider_config", "conditional_logic_between", "slider_response_values"),
        (ResponseType.TIME, "time_config", "conditional_logic_between", None),
        (ResponseType.TIMERANGE, "time_range_config", "conditional_logic_between", None),
        (
            ResponseType.NUMBERSELECT,
            "number_selection_config",
            "conditional_logic_between",
            "number_selection_response_values",
        ),
        (ResponseType.DATE, "date_config", "conditional_logic_equal", None),
        (
            ResponseType.SINGLESELECTROWS,
            "single_select_row_config",
            "conditional_logic_equal",
            "single_select_row_response_values",
        ),
        (
            ResponseType.MULTISELECTROWS,
            "multi_select_row_config",
            "conditional_logic_equal",
            "multi_select_row_response_values",
        ),
        (
            ResponseType.SLIDERROWS,
            "slider_rows_config",
            "conditional_logic_rows_outside_of",
            "slider_rows_response_values",
        ),
    ),
)
def test_create_activity_item_conditional_logic(
    base_item_data, request, response_type, config_fixture, cnd_logic_fixture, response_values_fixture
) -> None:
    config = request.getfixturevalue(config_fixture)
    cnd_logic = request.getfixturevalue(cnd_logic_fixture)
    if response_values_fixture:
        response_values = request.getfixturevalue(response_values_fixture)
    else:
        response_values = None
    ActivityItemCreate(
        **base_item_data.dict(),
        config=config,
        response_type=response_type,
        conditional_logic=cnd_logic,
        response_values=response_values,
    )
