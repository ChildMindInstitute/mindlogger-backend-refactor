import pytest

from apps.activities.domain.activity_create import ActivityItemCreate
from apps.activities.domain.response_type_config import (
    MultiSelectionConfig,
    MultiSelectionRowsConfig,
    ResponseType,
    SingleSelectionConfig,
    SingleSelectionRowsConfig,
    SliderConfig,
    SliderRowsConfig,
    TextConfig,
)
from apps.activities.domain.response_values import (
    MultiSelectionRowsValues,
    MultiSelectionValues,
    SingleSelectionRowsValues,
    SingleSelectionValues,
    SliderRowsValues,
    SliderValues,
)
from apps.activities.tests.utils import BaseItemData


@pytest.fixture
def base_item_data() -> BaseItemData:
    return BaseItemData()


@pytest.fixture
def single_select_item_create(
    base_item_data: BaseItemData,
    single_select_config: SingleSelectionConfig,
    single_select_response_values: SingleSelectionValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        response_type=ResponseType.SINGLESELECT,
        response_values=single_select_response_values,
        config=single_select_config,
        **base_item_data.dict(),
    )


@pytest.fixture
def multi_select_item_create(
    base_item_data: BaseItemData,
    multi_select_config: MultiSelectionConfig,
    multi_select_reponse_values: MultiSelectionValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        response_type=ResponseType.MULTISELECT,
        response_values=multi_select_reponse_values,
        config=multi_select_config,
        **base_item_data.dict(),
    )


@pytest.fixture
def slider_item_create(
    base_item_data: BaseItemData,
    slider_config: SliderConfig,
    slider_response_values: SliderValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        response_type=ResponseType.SLIDER,
        response_values=slider_response_values,
        config=slider_config,
        **base_item_data.dict(),
    )


@pytest.fixture
def single_select_row_item_create(
    base_item_data: BaseItemData,
    single_select_row_config: SingleSelectionRowsConfig,
    single_select_row_response_values: SingleSelectionRowsValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        config=single_select_row_config,
        response_values=single_select_row_response_values,
        response_type=ResponseType.SINGLESELECTROWS,
    )


@pytest.fixture
def multi_select_row_item_create(
    base_item_data: BaseItemData,
    multi_select_row_config: MultiSelectionRowsConfig,
    multi_select_row_response_values: MultiSelectionRowsValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        config=multi_select_row_config,
        response_values=multi_select_row_response_values,
        response_type=ResponseType.MULTISELECTROWS,
    )


@pytest.fixture
def slider_rows_item_create(
    base_item_data: BaseItemData,
    slider_rows_config: SliderRowsConfig,
    slider_rows_response_values: SliderRowsValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.SLIDERROWS,
        response_values=slider_rows_response_values,
        config=slider_rows_config,
    )


@pytest.fixture
def text_item_create(text_config: TextConfig, base_item_data: BaseItemData) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.TEXT,
        config=text_config,
    )
