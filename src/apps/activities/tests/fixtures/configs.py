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
    ParagraphTextConfig,
    PhotoConfig,
    PhrasalTemplateConfig,
    ResponseType,
    SingleSelectionConfig,
    SingleSelectionRowsConfig,
    SliderConfig,
    SliderRowsConfig,
    TextConfig,
    TimeConfig,
    TimeRangeConfig,
    UnityConfig,
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
        portrait_layout=False,
        set_alerts=False,
        add_tooltip=False,
        set_palette=False,
        response_data_identifier=False,
        **default_config.dict(),
        type=ResponseType.SINGLESELECT,
    )


@pytest.fixture
def multi_select_config(single_select_config: SingleSelectionConfig) -> MultiSelectionConfig:
    data = single_select_config.dict()
    data["type"] = ResponseType.MULTISELECT
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
        type=ResponseType.SLIDER,
    )


@pytest.fixture
def date_config(default_config: DefaultConfig) -> DateConfig:
    return DateConfig(**default_config.dict(), type=ResponseType.DATE)


@pytest.fixture
def number_selection_config(default_config: DefaultConfig) -> NumberSelectionConfig:
    return NumberSelectionConfig(**default_config.dict(), type=ResponseType.NUMBERSELECT)


@pytest.fixture
def time_config(default_config: DefaultConfig) -> TimeConfig:
    return TimeConfig(**default_config.dict(), type=ResponseType.TIME)


@pytest.fixture
def time_range_config(default_config: DefaultConfig) -> TimeRangeConfig:
    return TimeRangeConfig(**default_config.dict(), type=ResponseType.TIMERANGE)


@pytest.fixture
def single_select_row_config(default_config: DefaultConfig) -> SingleSelectionRowsConfig:
    return SingleSelectionRowsConfig(
        add_scores=False,
        set_alerts=False,
        add_tooltip=False,
        add_tokens=None,
        **default_config.dict(),
        type=ResponseType.SINGLESELECTROWS,
    )


@pytest.fixture
def multi_select_row_config(
    single_select_row_config: SingleSelectionRowsConfig,
) -> MultiSelectionRowsConfig:
    data = single_select_row_config.dict()
    data["type"] = ResponseType.MULTISELECTROWS
    return MultiSelectionRowsConfig(**data)


@pytest.fixture
def slider_rows_config(default_config: DefaultConfig) -> SliderRowsConfig:
    return SliderRowsConfig(add_scores=False, set_alerts=False, **default_config.dict(), type=ResponseType.SLIDERROWS)


@pytest.fixture
def text_config(default_config: DefaultConfig) -> TextConfig:
    return TextConfig(
        **default_config.dict(),
        correct_answer_required=False,
        numerical_response_required=False,
        response_data_identifier=False,
        response_required=False,
        type=ResponseType.TEXT,
    )


@pytest.fixture
def paragraph_text_config(default_config: DefaultConfig) -> ParagraphTextConfig:
    return ParagraphTextConfig(
        **default_config.dict(),
        response_required=False,
        type=ResponseType.PARAGRAPHTEXT,
    )


@pytest.fixture
def drawing_config(default_config: DefaultConfig) -> DrawingConfig:
    return DrawingConfig(remove_undo_button=False, **default_config.dict(), type=ResponseType.DRAWING)


@pytest.fixture
def photo_config(default_config: DefaultConfig) -> PhotoConfig:
    return PhotoConfig(**default_config.dict(), type=ResponseType.PHOTO)


@pytest.fixture
def video_config(default_config: DefaultConfig) -> VideoConfig:
    return VideoConfig(**default_config.dict(), type=ResponseType.VIDEO)


@pytest.fixture
def geolocation_config(default_config: DefaultConfig) -> GeolocationConfig:
    return GeolocationConfig(**default_config.dict(), type=ResponseType.GEOLOCATION)


@pytest.fixture
def audio_config(default_config: DefaultConfig) -> AudioConfig:
    return AudioConfig(**default_config.dict(), type=ResponseType.AUDIO)


@pytest.fixture
def message_config(default_config: DefaultConfig) -> MessageConfig:
    return MessageConfig(**default_config.dict(), type=ResponseType.MESSAGE)


@pytest.fixture
def audio_player_config(default_config: DefaultConfig) -> AudioPlayerConfig:
    return AudioPlayerConfig(**default_config.dict(), play_once=False, type=ResponseType.AUDIOPLAYER)


@pytest.fixture
def phrasal_template_config(default_config: DefaultConfig) -> PhrasalTemplateConfig:
    return PhrasalTemplateConfig(**default_config.dict(), type=ResponseType.PHRASAL_TEMPLATE)


@pytest.fixture
def unity_config(default_config: DefaultConfig) -> UnityConfig:
    return UnityConfig(**default_config.dict(), type=ResponseType.UNITY)
