from enum import Enum

from pydantic import NonNegativeInt, PositiveInt

from apps.activities.domain.response_values import ResponseValueConfigOptions
from apps.shared.domain import InternalModel


class AdditionalResponseOption(InternalModel):
    text_input_option: bool
    text_input_required: bool


class _ScreenConfig(InternalModel):
    remove_back_button: bool
    skippable_item: bool


class TextConfig(_ScreenConfig, InternalModel):
    max_response_length: PositiveInt = 300
    correct_answer_required: bool
    correct_answer: str | None = None
    numerical_response_required: bool
    response_data_identifier: bool
    response_required: bool


class SingleSelectionConfig(_ScreenConfig, InternalModel):
    randomize_options: bool
    timer: NonNegativeInt | None
    add_scores: bool
    set_alerts: bool
    add_tooltip: bool
    set_palette: bool
    additional_response_option: AdditionalResponseOption


class MultiSelectionConfig(SingleSelectionConfig, InternalModel):
    pass


class MessageConfig(InternalModel):
    remove_back_button: bool
    timer: NonNegativeInt | None


class SliderConfig(_ScreenConfig, InternalModel):
    add_scores: bool
    set_alerts: bool
    additional_response_option: AdditionalResponseOption
    show_tick_marks: bool
    show_tick_labels: bool
    continuous_slider: bool
    timer: NonNegativeInt | None


class NumberSelectionConfig(_ScreenConfig, InternalModel):
    additional_response_option: AdditionalResponseOption


class _DefaultConfig(_ScreenConfig, InternalModel):
    additional_response_option: AdditionalResponseOption
    timer: NonNegativeInt | None


class TimeRangeConfig(_DefaultConfig, InternalModel):
    pass


class GeolocationConfig(_DefaultConfig, InternalModel):
    pass


class DrawingConfig(_ScreenConfig, InternalModel):
    additional_response_option: AdditionalResponseOption
    timer: NonNegativeInt | None
    remove_undo_button: bool = False
    navigation_to_top: bool = False


class PhotoConfig(_DefaultConfig, InternalModel):
    pass


class VideoConfig(_DefaultConfig, InternalModel):
    pass


class DateConfig(_DefaultConfig, InternalModel):
    pass


class SliderRowsConfig(_ScreenConfig, InternalModel):
    add_scores: bool
    set_alerts: bool
    timer: NonNegativeInt | None


class SingleSelectionRowsConfig(_ScreenConfig, InternalModel):
    timer: NonNegativeInt | None
    add_scores: bool
    set_alerts: bool
    add_tooltip: bool


class MultiSelectionRowsConfig(SingleSelectionRowsConfig, InternalModel):
    pass


class AudioConfig(_DefaultConfig, InternalModel):
    pass


class AudioPlayerConfig(_ScreenConfig, InternalModel):
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
    MESSAGE = "message"
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
    # FLANKER = "flanker"
    # ABTEST = "abTest"


ResponseTypeConfigOptions = [
    TextConfig,
    SingleSelectionConfig,
    MultiSelectionConfig,
    MessageConfig,
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
]


ResponseTypeConfig = (
    TextConfig
    | SingleSelectionConfig
    | MultiSelectionConfig
    | MessageConfig
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
