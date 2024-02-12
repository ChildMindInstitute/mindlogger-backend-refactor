import pytest

from apps.activities.domain.response_type_config import (
    AdditionalResponseOption,
    DateConfig,
    DrawingConfig,
    MultiSelectionConfig,
    MultiSelectionRowsConfig,
    SingleSelectionConfig,
    SingleSelectionRowsConfig,
    SliderConfig,
    SliderRowsConfig,
    TextConfig,
)


@pytest.fixture
def additional_response_option() -> AdditionalResponseOption:
    return AdditionalResponseOption(text_input_option=False, text_input_required=False)


@pytest.fixture
def single_select_config(
    additional_response_option: AdditionalResponseOption,
) -> SingleSelectionConfig:
    return SingleSelectionConfig(
        randomize_options=False,
        timer=0,
        add_scores=False,
        add_tokens=False,
        set_alerts=False,
        add_tooltip=False,
        set_palette=False,
        remove_back_button=False,
        skippable_item=False,
        additional_response_option=additional_response_option,
    )


@pytest.fixture
def multi_select_config(single_select_config) -> MultiSelectionConfig:
    data = single_select_config.dict()
    return MultiSelectionConfig(**data)


@pytest.fixture
def slider_config(
    additional_response_option: AdditionalResponseOption,
) -> SliderConfig:
    return SliderConfig(
        timer=0,
        add_scores=False,
        set_alerts=False,
        remove_back_button=False,
        skippable_item=False,
        show_tick_marks=False,
        show_tick_labels=False,
        continuous_slider=False,
        additional_response_option=additional_response_option,
    )


@pytest.fixture
def date_config(
    additional_response_option: AdditionalResponseOption,
) -> DateConfig:
    return DateConfig(
        remove_back_button=False,
        skippable_item=False,
        timer=0,
        additional_response_option=additional_response_option,
    )


@pytest.fixture
def text_config() -> TextConfig:
    return TextConfig(
        remove_back_button=False,
        skippable_item=False,
        correct_answer_required=False,
        numerical_response_required=False,
        response_data_identifier=False,
        response_required=False,
    )


@pytest.fixture
def drawing_config(
    additional_response_option: AdditionalResponseOption,
) -> DrawingConfig:
    return DrawingConfig(
        remove_back_button=False,
        remove_undo_button=False,
        additional_response_option=additional_response_option,
        skippable_item=False,
        timer=0,
    )


@pytest.fixture
def slider_rows_config() -> SliderRowsConfig:
    return SliderRowsConfig(
        remove_back_button=False,
        skippable_item=False,
        add_scores=False,
        set_alerts=False,
        timer=0,
    )


@pytest.fixture
def single_select_row_config() -> SingleSelectionRowsConfig:
    return SingleSelectionRowsConfig(
        timer=0,
        add_scores=False,
        set_alerts=False,
        add_tooltip=False,
        add_tokens=None,
        remove_back_button=False,
        skippable_item=False,
    )


@pytest.fixture
def multi_select_row_config(
    single_select_row_config: SingleSelectionRowsConfig,
) -> MultiSelectionRowsConfig:
    return MultiSelectionRowsConfig(**single_select_row_config.dict())


@pytest.fixture(scope="session")
def item_config() -> SingleSelectionConfig:
    return SingleSelectionConfig(
        randomize_options=False,
        timer=0,
        add_scores=False,
        add_tokens=False,
        set_alerts=False,
        add_tooltip=False,
        set_palette=False,
        remove_back_button=False,
        skippable_item=False,
        additional_response_option=AdditionalResponseOption(text_input_option=False, text_input_required=False),
    )
