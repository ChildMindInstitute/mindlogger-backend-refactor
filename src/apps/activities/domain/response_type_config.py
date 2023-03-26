from enum import Enum

from pydantic import NonNegativeInt

from apps.shared.domain import InternalModel


class AdditionalResponseOption(InternalModel):
    text_input_option: bool = False
    text_input_required: bool = False


class _ScreenConfig(InternalModel):
    remove_back_button: bool = False
    skippable_item: bool = False


class TextConfig(_ScreenConfig, InternalModel):
    max_response_length: int = -1
    correct_answer_required: bool = False
    correct_answer: str = ""
    numerical_response_required: bool = False
    response_data_identifier: str = ""
    response_required: bool = False


class SingleSelectionConfig(_ScreenConfig, InternalModel):
    randomize_options: bool
    timer: NonNegativeInt
    add_scores: bool
    set_alerts: bool
    add_tooltip: bool
    set_palette: bool
    additional_response_option: AdditionalResponseOption


class MultiSelectionConfig(SingleSelectionConfig, InternalModel):
    pass


class MessageConfig(InternalModel):
    remove_back_button: bool = False
    timer: NonNegativeInt = 0


class SliderConfig(_ScreenConfig, InternalModel):
    add_scores: bool
    set_alerts: bool
    additional_response_option: AdditionalResponseOption
    show_tick_marks: bool
    show_tick_labels: bool
    continuous_slider: bool
    timer: NonNegativeInt


class NumberSelectionConfig(_ScreenConfig, InternalModel):
    additional_response_option: AdditionalResponseOption


class _DefaultConfig(_ScreenConfig, InternalModel):
    additional_response_option: AdditionalResponseOption
    timer: NonNegativeInt = 0


class TimeRangeConfig(_DefaultConfig, InternalModel):
    pass


class GeolocationConfig(_DefaultConfig, InternalModel):
    pass


class DrawingConfig(_ScreenConfig, InternalModel):
    additional_response_option: AdditionalResponseOption
    timer: NonNegativeInt = 0
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
    timer: NonNegativeInt


class SingleSelectionRowsConfig(_ScreenConfig, InternalModel):
    timer: NonNegativeInt
    add_scores: bool
    set_alerts: bool
    add_tooltip: bool


class MultiSelectionRowsConfig(SingleSelectionRowsConfig, InternalModel):
    pass


class AudioConfig(_DefaultConfig, InternalModel):
    pass


class AudioPlayerConfig(_ScreenConfig, InternalModel):
    additional_response_option: AdditionalResponseOption
    play_once: bool = False


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
