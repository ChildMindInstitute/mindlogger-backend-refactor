from enum import Enum

from pydantic import Field, NonNegativeInt, root_validator, validator
from pydantic.color import Color

from apps.shared.domain import (
    InternalModel,
    validate_audio,
    validate_color,
    validate_image,
)


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


class _SingleSelectionValue(InternalModel):
    text: str
    image: str
    score: int
    tooltip: str
    is_hidden: bool
    color: Color

    @validator("image")
    def validate_image(cls, value):
        return validate_image(value)

    @validator("color")
    def validate_color(cls, value):
        return validate_color(value)


class SingleSelectionValues(InternalModel):
    options: list[_SingleSelectionValue]


class MultiSelectionConfig(SingleSelectionConfig, InternalModel):
    pass


class MultiSelectionValues(SingleSelectionValues, InternalModel):
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


class SliderValues(InternalModel):
    min_label: str = Field(..., max_length=20)
    max_label: str = Field(..., max_length=20)
    min_value: NonNegativeInt = Field(default=0, max_value=11)
    max_value: NonNegativeInt = Field(default=12, max_value=12)
    min_image: str
    max_image: str

    @validator("min_image", "max_image")
    def validate_image(cls, value):
        return validate_image(value)

    @root_validator
    def validate_min_max(cls, values):
        if values.get("min_value") >= values.get("max_value"):
            raise ValueError("min_value must be less than max_value")
        return values


class NumberSelectionConfig(_ScreenConfig, InternalModel):
    additional_response_option: AdditionalResponseOption


class NumberSelectionValues(InternalModel):
    min_value: NonNegativeInt = Field(default=0)
    max_value: NonNegativeInt = Field(default=100)

    @root_validator
    def validate_min_max(cls, values):
        if values.get("min_value") >= values.get("max_value"):
            raise ValueError("min_value must be less than max_value")
        return values


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


class DrawingValues(InternalModel):
    drawing_example: str
    drawing_background: str

    @validator("drawing_example", "drawing_background")
    def validate_image(cls, value):
        return validate_image(value)


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


class SliderRowsValue(SliderValues, InternalModel):
    label: str = Field(..., max_length=11)


class SliderRowsValues(InternalModel):
    rows: list[SliderRowsValue]


class SingleSelectionRowsConfig(_ScreenConfig, InternalModel):
    timer: NonNegativeInt
    add_scores: bool
    set_alerts: bool
    add_tooltip: bool


class _SingleSelectionRowValue(InternalModel):
    text: str
    image: str
    score: int
    tooltip: str

    @validator("image")
    def validate_image(cls, value):
        return validate_image(value)


class _SingleSelectionRowsValue(InternalModel):
    row_name: str
    row_image: str
    tooltip: str
    options: list[_SingleSelectionRowValue]

    @validator("row_image")
    def validate_image(cls, value):
        return validate_image(value)


class SingleSelectionRowsValues(InternalModel):
    rows: list[_SingleSelectionRowsValue]


class MultiSelectionRowsConfig(SingleSelectionRowsConfig, InternalModel):
    pass


class MultiSelectionRowsValues(SingleSelectionRowsValues, InternalModel):
    pass


class AudioConfig(_DefaultConfig, InternalModel):
    pass


class AudioValues(InternalModel):
    max_duration: NonNegativeInt = 300


class AudioPlayerConfig(_ScreenConfig, InternalModel):
    additional_response_option: AdditionalResponseOption
    play_once: bool = False


class AudioPlayerValues(InternalModel):
    file: str

    @validator("file")
    def validate_file(cls, value):
        return validate_audio(value)


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
