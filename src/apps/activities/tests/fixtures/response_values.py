import uuid
from typing import cast

import pytest

from apps.activities.domain.response_values import (
    DrawingValues,
    MultiSelectionRowsValues,
    MultiSelectionValues,
    NumberSelectionValues,
    SingleSelectionRowsValues,
    SingleSelectionValues,
    SliderRowsValue,
    SliderRowsValues,
    SliderValueAlert,
    SliderValues,
    _SingleSelectionDataOption,
    _SingleSelectionDataRow,
    _SingleSelectionOption,
    _SingleSelectionRow,
    _SingleSelectionValue,
)


@pytest.fixture
def single_select_response_values() -> SingleSelectionValues:
    return SingleSelectionValues(
        palette_name=None,
        options=[
            _SingleSelectionValue(
                id=str(uuid.uuid4()),
                text="text",
                image=None,
                score=None,
                tooltip=None,
                is_hidden=False,
                color=None,
                value=0,
            )
        ],
    )


@pytest.fixture
def multi_select_reponse_values(
    single_select_response_values: SingleSelectionValues,
) -> MultiSelectionValues:
    data = single_select_response_values.dict()
    return MultiSelectionValues(**data)


@pytest.fixture
def slider_value_alert() -> SliderValueAlert:
    return SliderValueAlert(value=0, min_value=None, max_value=None, alert="alert")


@pytest.fixture
def slider_response_values() -> SliderValues:
    return SliderValues(
        min_label=None,
        max_label=None,
        scores=None,
        alerts=None,
    )


@pytest.fixture
def number_select_response_values() -> NumberSelectionValues:
    return NumberSelectionValues()


@pytest.fixture
def drawing_response_values(remote_image: str) -> DrawingValues:
    return DrawingValues(drawing_background=remote_image, drawing_example=remote_image)


@pytest.fixture
def slider_rows_response_values() -> SliderRowsValues:
    return SliderRowsValues(
        rows=[
            SliderRowsValue(
                id=str(uuid.uuid4()),
                min_label=None,
                max_label=None,
                label="label",
            )
        ]
    )


@pytest.fixture
def single_select_row_option() -> _SingleSelectionOption:
    return _SingleSelectionOption(id=str(uuid.uuid4()), text="text")


@pytest.fixture
def single_select_row() -> _SingleSelectionRow:
    return _SingleSelectionRow(id=str(uuid.uuid4()), row_name="row_name")


@pytest.fixture
def signle_select_row_data_option(
    single_select_row_option: _SingleSelectionOption,
) -> _SingleSelectionDataOption:
    option_id = cast(str, single_select_row_option.id)
    return _SingleSelectionDataOption(option_id=option_id)


@pytest.fixture
def single_select_row_data_row(
    single_select_row: _SingleSelectionRow,
    signle_select_row_data_option: _SingleSelectionDataOption,
) -> _SingleSelectionDataRow:
    row_id = cast(str, single_select_row.id)
    return _SingleSelectionDataRow(row_id=row_id, options=[signle_select_row_data_option])


@pytest.fixture
def single_select_row_response_values(
    single_select_row_option: _SingleSelectionOption,
    single_select_row: _SingleSelectionRow,
    single_select_row_data_row: _SingleSelectionDataRow,
) -> SingleSelectionRowsValues:
    return SingleSelectionRowsValues(
        rows=[single_select_row],
        options=[single_select_row_option],
        data_matrix=[single_select_row_data_row],
    )


@pytest.fixture
def multi_select_row_response_values(
    single_select_row_response_values: SingleSelectionRowsValues,
) -> MultiSelectionRowsValues:
    return MultiSelectionRowsValues(**single_select_row_response_values.dict())


@pytest.fixture(scope="session")
def item_response_values() -> SingleSelectionValues:
    return SingleSelectionValues(
        palette_name=None,
        options=[
            _SingleSelectionValue(
                id=str(uuid.uuid4()),
                text="text",
                image=None,
                score=None,
                tooltip=None,
                is_hidden=False,
                color=None,
                value=0,
            )
        ],
    )
