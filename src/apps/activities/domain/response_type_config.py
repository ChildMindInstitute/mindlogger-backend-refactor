from enum import Enum

from pydantic import Field, NonNegativeInt, PositiveInt, validator

from apps.activities.domain.constants_flanker import (
    FLANKER_PRACTISE_BLOCKS,
    FLANKER_TEST_BLOCKS,
    BlockSettings,
    FlankerBaseConfig,
)
from apps.activities.domain.response_values import ResponseValueConfigOptions
from apps.activities.errors import CorrectAnswerRequiredError
from apps.shared.domain import PublicModel


class AdditionalResponseOption(PublicModel):
    text_input_option: bool
    text_input_required: bool


class _ScreenConfig(PublicModel):
    remove_back_button: bool
    skippable_item: bool


class TextConfig(_ScreenConfig, PublicModel):
    max_response_length: PositiveInt = 300
    correct_answer_required: bool
    correct_answer: str | None = Field(
        default=None,
        max_length=300,
        description="Required if correct_answer_required is True",
    )
    numerical_response_required: bool
    response_data_identifier: bool
    response_required: bool
    is_identifier: bool | None = None

    @validator("correct_answer")
    def validate_correct_answer(cls, value, values):
        # correct_answer must be set if correct_answer_required is True
        if values.get("correct_answer_required") and not value:
            raise CorrectAnswerRequiredError()
        return value


class SingleSelectionConfig(_ScreenConfig, PublicModel):
    randomize_options: bool
    timer: NonNegativeInt | None
    add_scores: bool
    set_alerts: bool
    add_tooltip: bool
    set_palette: bool
    add_tokens: bool | None
    additional_response_option: AdditionalResponseOption


class MultiSelectionConfig(SingleSelectionConfig, PublicModel):
    pass


class MessageConfig(PublicModel):
    remove_back_button: bool
    timer: NonNegativeInt | None


class SliderConfig(_ScreenConfig, PublicModel):
    add_scores: bool
    set_alerts: bool
    additional_response_option: AdditionalResponseOption
    show_tick_marks: bool
    show_tick_labels: bool
    continuous_slider: bool
    timer: NonNegativeInt | None


class NumberSelectionConfig(_ScreenConfig, PublicModel):
    additional_response_option: AdditionalResponseOption


class DefaultConfig(_ScreenConfig, PublicModel):
    additional_response_option: AdditionalResponseOption
    timer: NonNegativeInt | None


class TimeRangeConfig(DefaultConfig, PublicModel):
    pass


class TimeConfig(DefaultConfig, PublicModel):
    pass


class GeolocationConfig(DefaultConfig, PublicModel):
    pass


class DrawingConfig(_ScreenConfig, PublicModel):
    additional_response_option: AdditionalResponseOption
    timer: NonNegativeInt | None
    remove_undo_button: bool = False
    navigation_to_top: bool = False


class PhotoConfig(DefaultConfig, PublicModel):
    pass


class VideoConfig(DefaultConfig, PublicModel):
    pass


class DateConfig(DefaultConfig, PublicModel):
    pass


class SliderRowsConfig(_ScreenConfig, PublicModel):
    add_scores: bool
    set_alerts: bool
    timer: NonNegativeInt | None


class SingleSelectionRowsConfig(_ScreenConfig, PublicModel):
    timer: NonNegativeInt | None
    add_scores: bool
    set_alerts: bool
    add_tooltip: bool
    add_tokens: bool | None


class MultiSelectionRowsConfig(SingleSelectionRowsConfig, PublicModel):
    pass


class AudioConfig(DefaultConfig, PublicModel):
    pass


class AudioPlayerConfig(_ScreenConfig, PublicModel):
    additional_response_option: AdditionalResponseOption
    play_once: bool


class GyroscopeGeneralSettings(PublicModel):
    instruction: str
    number_of_trials: int
    length_of_test: int
    lambda_slope: int


class GyroscopePracticeSettings(PublicModel):
    instruction: str


class GyroscopeTestSettings(PublicModel):
    instruction: str


class GyroscopeConfig(PublicModel):
    name: str
    description: str | None
    is_hidden: bool | None
    general: GyroscopeGeneralSettings
    practice: GyroscopePracticeSettings
    test: GyroscopeTestSettings


class TouchGeneralSettings(PublicModel):
    instruction: str
    number_of_trials: int
    length_of_test: int
    lambda_slope: int


class TouchPracticeSettings(PublicModel):
    instruction: str


class TouchTestSettings(PublicModel):
    instruction: str


class TouchConfig(PublicModel):
    name: str
    description: str | None
    is_hidden: bool | None
    general: TouchGeneralSettings
    practice: TouchPracticeSettings
    test: TouchTestSettings


class FlankerPractiseConfig(FlankerBaseConfig):
    blocks: list[BlockSettings] = FLANKER_PRACTISE_BLOCKS
    block_type: str = "practice"


class FlankerTestConfig(FlankerBaseConfig):
    blocks: list[BlockSettings] = FLANKER_TEST_BLOCKS
    block_type: str = "test"


class ABTrailsIpadConfig(PublicModel):
    description: str
    image_placeholder: str


class ABTrailsMobileConfig(PublicModel):
    description: str
    image_placeholder: str


class NoneResponseType(str, Enum):
    TEXT = "text"
    MESSAGE = "message"
    TIMERANGE = "timeRange"
    GEOLOCATION = "geolocation"
    PHOTO = "photo"
    VIDEO = "video"
    DATE = "date"
    TIME = "time"
    FLANKERPRACTISE = "flankerPractise"
    FLANKERTEST = "flankerTest"
    GYROSCOPE = "gyroscope"
    TOUCH = "touch"
    ABTRAILSIPAD = "ABTrailsIpad"
    ABTRAILSMOBILE = "ABTrailsMobile"


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
    TIME = "time"
    FLANKERPRACTISE = "flankerPractise"
    FLANKERTEST = "flankerTest"
    GYROSCOPE = "gyroscope"
    TOUCH = "touch"
    ABTRAILSIPAD = "ABTrailsIpad"
    ABTRAILSMOBILE = "ABTrailsMobile"


class PerformanceTaskType(str, Enum):
    FLANKER = "flanker"
    GYROSCOPE = "gyroscope"
    TOUCH = "touch"
    ABTRAILSIPAD = "ABTrailsIpad"
    ABTRAILSMOBILE = "ABTrailsMobile"


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
    TimeConfig,
    FlankerPractiseConfig,
    FlankerTestConfig,
    GyroscopeConfig,
    TouchConfig,
    ABTrailsIpadConfig,
    ABTrailsMobileConfig,
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
    | TimeConfig
    | FlankerPractiseConfig
    | FlankerTestConfig
    | GyroscopeConfig
    | TouchConfig
    | ABTrailsIpadConfig
    | ABTrailsMobileConfig
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
