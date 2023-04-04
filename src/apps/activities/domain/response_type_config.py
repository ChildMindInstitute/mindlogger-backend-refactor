from enum import Enum

from pydantic import BaseModel, NonNegativeInt, PositiveInt

from apps.activities.domain.response_values import (
    ResponseValueConfigOptions,
    SingleSelectionRowsValues,
    SingleSelectionValues,
)


class AdditionalResponseOption(BaseModel):
    text_input_option: bool
    text_input_required: bool


class _ScreenConfig(BaseModel):
    remove_back_button: bool
    skippable_item: bool


class TextConfig(_ScreenConfig, BaseModel):
    max_response_length: PositiveInt = 300
    correct_answer_required: bool
    correct_answer: str | None = None
    numerical_response_required: bool
    response_data_identifier: bool
    response_required: bool


class SingleSelectionConfig(_ScreenConfig, BaseModel):
    randomize_options: bool
    timer: NonNegativeInt | None
    add_scores: bool
    set_alerts: bool
    add_tooltip: bool
    set_palette: bool
    additional_response_option: AdditionalResponseOption


class MultiSelectionConfig(SingleSelectionConfig, BaseModel):
    pass


class MessageConfig(BaseModel):
    remove_back_button: bool
    timer: NonNegativeInt | None


class SliderConfig(_ScreenConfig, BaseModel):
    add_scores: bool
    set_alerts: bool
    additional_response_option: AdditionalResponseOption
    show_tick_marks: bool
    show_tick_labels: bool
    continuous_slider: bool
    timer: NonNegativeInt | None


class NumberSelectionConfig(_ScreenConfig, BaseModel):
    additional_response_option: AdditionalResponseOption


class DefaultConfig(_ScreenConfig, BaseModel):
    additional_response_option: AdditionalResponseOption
    timer: NonNegativeInt | None


class TimeRangeConfig(DefaultConfig, BaseModel):
    pass


class GeolocationConfig(DefaultConfig, BaseModel):
    pass


class DrawingConfig(_ScreenConfig, BaseModel):
    additional_response_option: AdditionalResponseOption
    timer: NonNegativeInt | None
    remove_undo_button: bool = False
    navigation_to_top: bool = False


class PhotoConfig(DefaultConfig, BaseModel):
    pass


class VideoConfig(DefaultConfig, BaseModel):
    pass


class DateConfig(DefaultConfig, BaseModel):
    pass


class SliderRowsConfig(_ScreenConfig, BaseModel):
    add_scores: bool
    set_alerts: bool
    timer: NonNegativeInt | None


class SingleSelectionRowsConfig(_ScreenConfig, BaseModel):
    timer: NonNegativeInt | None
    add_scores: bool
    set_alerts: bool
    add_tooltip: bool


class MultiSelectionRowsConfig(SingleSelectionRowsConfig, BaseModel):
    pass


class AudioConfig(DefaultConfig, BaseModel):
    pass


class AudioPlayerConfig(_ScreenConfig, BaseModel):
    additional_response_option: AdditionalResponseOption
    play_once: bool


class NoneResponseType(str, Enum):
    TEXT = "text"
    MESSAGE = "message"
    TIMERANGE = "timeRange"
    GEOLOCATION = "geolocation"
    PHOTO = "photo"
    VIDEO = "video"
    DATE = "date"


class ResponseType(str, Enum):
    TEXT = "text"
    SINGLESELECT = "singleSelect"
    MULTISELECT = "multiSelect"
    SLIDER = "slider"
    NUMBERSELECT = "numberSelect"
    TIMERANGE = "timeRange"
    GEOLOCATION = "geolocation"
    DRAWING = "drawing"
    PHOTO = "photo"
    VIDEO = "video"
    DATE = "date"
    SLIDERROWS = "sliderRows"
    SINGLESELECTROWS = "singleSelectRows"
    MULTISELECTROWS = "multiSelectRows"
    AUDIO = "audio"
    AUDIOPLAYER = "audioPlayer"
    MESSAGE = "message"
    # FLANKER = "flanker"
    # ABTEST = "abTest"


ResponseTypeConfigOptions = [
    TextConfig,
    SingleSelectionConfig,
    MultiSelectionConfig,
    SliderConfig,
    NumberSelectionConfig,
    TimeRangeConfig,
    GeolocationConfig,
    DrawingConfig,
    PhotoConfig,
    VideoConfig,
    DateConfig,
    SliderRowsConfig,
    SingleSelectionRowsConfig,
    MultiSelectionRowsConfig,
    AudioConfig,
    AudioPlayerConfig,
    MessageConfig,
]


ResponseTypeConfig = (
    TextConfig
    | SingleSelectionConfig
    | MultiSelectionConfig
    | SliderConfig
    | NumberSelectionConfig
    | TimeRangeConfig
    | GeolocationConfig
    | DrawingConfig
    | PhotoConfig
    | VideoConfig
    | DateConfig
    | SliderRowsConfig
    | SingleSelectionRowsConfig
    | MultiSelectionRowsConfig
    | AudioConfig
    | AudioPlayerConfig
    | MessageConfig
)

ResponseTypeValueConfig = {}
index = 0

for response_type in ResponseType:
    zipped_type_value = list(
        zip(ResponseValueConfigOptions, ResponseTypeConfigOptions)
    )

    ResponseTypeValueConfig[response_type] = {
        "config": zipped_type_value[index][1],
        "value": zipped_type_value[index][0],
    }
    index += 1

ResponseTypeValueConfig[ResponseType.MULTISELECT] = {
    "config": SingleSelectionConfig,
    "value": SingleSelectionValues,
}

ResponseTypeValueConfig[ResponseType.MULTISELECTROWS] = {
    "config": SingleSelectionRowsConfig,
    "value": SingleSelectionRowsValues,
}

ResponseTypeValueConfig[ResponseType.GEOLOCATION]["config"] = TimeRangeConfig
ResponseTypeValueConfig[ResponseType.PHOTO]["config"] = TimeRangeConfig
ResponseTypeValueConfig[ResponseType.VIDEO]["config"] = TimeRangeConfig
ResponseTypeValueConfig[ResponseType.DATE]["config"] = TimeRangeConfig
ResponseTypeValueConfig[ResponseType.AUDIO]["config"] = TimeRangeConfig
