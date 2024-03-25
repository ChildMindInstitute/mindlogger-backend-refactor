import pytest

from apps.activities.domain.response_type_config import (
    AdditionalResponseOption,
    AudioConfig,
    AudioPlayerConfig,
    DateConfig,
    DefaultConfig,
    DrawingConfig,
    GeolocationConfig,
    MessageConfig,
    MultiSelectionConfig,
    MultiSelectionRowsConfig,
    NumberSelectionConfig,
    PhotoConfig,
    SingleSelectionConfig,
    SingleSelectionRowsConfig,
    SliderConfig,
    SliderRowsConfig,
    TextConfig,
    TimeConfig,
    TimeRangeConfig,
    VideoConfig,
)


@pytest.fixture
def additional_response_option() -> AdditionalResponseOption:
    return AdditionalResponseOption(text_input_option=False, text_input_required=False)


@pytest.fixture
def default_config(additional_response_option: AdditionalResponseOption) -> DefaultConfig:
    return DefaultConfig(
        remove_back_button=False, skippable_item=False, additional_response_option=additional_response_option, timer=0
    )


@pytest.fixture
def single_select_config(default_config: DefaultConfig) -> SingleSelectionConfig:
    return SingleSelectionConfig(
        randomize_options=False,
        add_scores=False,
        add_tokens=False,
        set_alerts=False,
        add_tooltip=False,
        set_palette=False,
        **default_config.dict(),
    )


@pytest.fixture
def multi_select_config(single_select_config: SingleSelectionConfig) -> MultiSelectionConfig:
    data = single_select_config.dict()
    return MultiSelectionConfig(**data)


@pytest.fixture
def slider_config(default_config: DefaultConfig) -> SliderConfig:
    return SliderConfig(
        add_scores=False,
        set_alerts=False,
        show_tick_marks=False,
        show_tick_labels=False,
        continuous_slider=False,
        **default_config.dict(),
    )


@pytest.fixture
def date_config(default_config: DefaultConfig) -> DateConfig:
    return DateConfig(**default_config.dict())


@pytest.fixture
def number_selection_config(default_config: DefaultConfig) -> NumberSelectionConfig:
    return NumberSelectionConfig(**default_config.dict())


@pytest.fixture
def time_config(default_config: DefaultConfig) -> TimeConfig:
    return TimeConfig(**default_config.dict())


@pytest.fixture
def time_range_config(default_config: DefaultConfig) -> TimeRangeConfig:
    return TimeRangeConfig(**default_config.dict())


@pytest.fixture
def single_select_row_config(default_config: DefaultConfig) -> SingleSelectionRowsConfig:
    return SingleSelectionRowsConfig(
        add_scores=False, set_alerts=False, add_tooltip=False, add_tokens=None, **default_config.dict()
    )


@pytest.fixture
def multi_select_row_config(
    single_select_row_config: SingleSelectionRowsConfig,
) -> MultiSelectionRowsConfig:
    return MultiSelectionRowsConfig(**single_select_row_config.dict())


@pytest.fixture
def slider_rows_config(default_config: DefaultConfig) -> SliderRowsConfig:
    return SliderRowsConfig(add_scores=False, set_alerts=False, **default_config.dict())


@pytest.fixture
def text_config(default_config: DefaultConfig) -> TextConfig:
    return TextConfig(
        **default_config.dict(),
        correct_answer_required=False,
        numerical_response_required=False,
        response_data_identifier=False,
        response_required=False,
    )


@pytest.fixture
def drawing_config(default_config: DefaultConfig) -> DrawingConfig:
    return DrawingConfig(remove_undo_button=False, **default_config.dict())


@pytest.fixture
def photo_config(default_config: DefaultConfig) -> PhotoConfig:
    return PhotoConfig(**default_config.dict())


@pytest.fixture
def video_config(default_config: DefaultConfig) -> VideoConfig:
    return VideoConfig(**default_config.dict())


@pytest.fixture
def geolocation_config(default_config: DefaultConfig) -> GeolocationConfig:
    return GeolocationConfig(**default_config.dict())


@pytest.fixture
def audio_config(default_config: DefaultConfig) -> AudioConfig:
    return AudioConfig(**default_config.dict())


@pytest.fixture
def message_config(default_config: DefaultConfig) -> MessageConfig:
    return MessageConfig(**default_config.dict())


@pytest.fixture
def audio_player_config(default_config: DefaultConfig) -> AudioPlayerConfig:
    return AudioPlayerConfig(**default_config.dict(), play_once=False)
