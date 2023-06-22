from enum import Enum

from pydantic import Field, NonNegativeInt, PositiveInt, validator

from apps.activities.domain.constants_ab_trails_mobile import (
    MOBILE_NODES_FIRST,
    MOBILE_NODES_FOURTH,
    MOBILE_NODES_SECOND,
    MOBILE_NODES_THIRD,
    MOBILE_TUTORIALS_FIRST,
    MOBILE_TUTORIALS_FOURTH,
    MOBILE_TUTORIALS_SECOND,
    MOBILE_TUTORIALS_THIRD,
    ABTrailsMobileTutorial,
    MobileNodes,
)
from apps.activities.domain.constants_ab_trails_tablet import (
    TABLET_NODES_FIRST,
    TABLET_NODES_FOURTH,
    TABLET_NODES_SECOND,
    TABLET_NODES_THIRD,
    TABLET_TUTORIALS_FIRST,
    TABLET_TUTORIALS_FOURTH,
    TABLET_TUTORIALS_SECOND,
    TABLET_TUTORIALS_THIRD,
    ABTrailsTabletTutorial,
    TabletNodes,
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


class Phase(str, Enum):
    PRACTISE = "practise"
    TEST = "test"


class GyroscopePractiseConfig(PublicModel):
    phase: Phase
    trials_number: int
    duration_minutes: int
    lambda_slope: float


class GyroscopeTestConfig(GyroscopePractiseConfig):
    pass


class TouchPractiseConfig(PublicModel):
    phase: Phase
    trials_number: int
    duration_minutes: int
    lambda_slope: float


class TouchTestConfig(TouchPractiseConfig):
    pass


class CorrectPress(str, Enum):
    LEFT = "left"
    RIGHT = "right"


class ButtonSetting(PublicModel):
    name: str | None
    image: str | None


class FixationSettings(PublicModel):
    image: str | None
    duration: int


class StimulusId(str):
    pass


class BlockSettings(PublicModel):
    order: list[StimulusId]
    name: str


class StimulusSettings(PublicModel):
    id: StimulusId
    image: str
    correct_press: CorrectPress


class FlankerGeneralSettings(PublicModel):
    instruction: str
    buttons: list[ButtonSetting]
    fixation: FixationSettings | None
    stimulus_trials: list[StimulusSettings]


class FlankerTestSettings(PublicModel):
    instruction: str
    blocks: list[BlockSettings]
    stimulus_duration: int
    randomize_order: bool
    show_feedback: bool
    show_summary: bool


class FlankerPracticeSettings(FlankerTestSettings, PublicModel):
    threshold: int


class FlankerConfig(PublicModel):
    general: FlankerGeneralSettings
    practice: FlankerPracticeSettings
    test: FlankerTestSettings


class ABTrailsTabletFirstConfig(PublicModel):
    tablet_tutorials: ABTrailsTabletTutorial = TABLET_TUTORIALS_FIRST
    tablet_nodes: TabletNodes = TABLET_NODES_FIRST
    name: str = "trail1"
    question: str = "Test"
    description: str = "trail1"
    device_type: str


class ABTrailsTabletSecondConfig(PublicModel):
    tablet_tutorials: ABTrailsTabletTutorial = TABLET_TUTORIALS_SECOND
    tablet_nodes: TabletNodes = TABLET_NODES_SECOND
    name: str = "trail2"
    question: str = "Test"
    description: str = "trail2"
    device_type: str


class ABTrailsTabletThirdConfig(PublicModel):
    tablet_tutorials: ABTrailsTabletTutorial = TABLET_TUTORIALS_THIRD
    tablet_nodes: TabletNodes = TABLET_NODES_THIRD
    name: str = "trail3"
    question: str = "Test"
    description: str = "trail3"
    device_type: str


class ABTrailsTabletFourthConfig(PublicModel):
    tablet_tutorials: ABTrailsTabletTutorial = TABLET_TUTORIALS_FOURTH
    tablet_nodes: TabletNodes = TABLET_NODES_FOURTH
    name: str = "trail4"
    question: str = "Test"
    description: str = "trail4"
    device_type: str


class ABTrailsMobileFirstConfig(PublicModel):
    mobile_tutorials: ABTrailsMobileTutorial = MOBILE_TUTORIALS_FIRST
    mobile_nodes: MobileNodes = MOBILE_NODES_FIRST
    name: str = "trail1"
    question: str = "Test"
    description: str = "trail1"
    device_type: str


class ABTrailsMobileSecondConfig(PublicModel):
    mobile_tutorials: ABTrailsMobileTutorial = MOBILE_TUTORIALS_SECOND
    mobile_nodes: MobileNodes = MOBILE_NODES_SECOND
    name: str = "trail2"
    question: str = "Test"
    description: str = "trail2"
    device_type: str


class ABTrailsMobileThirdConfig(PublicModel):
    mobile_tutorials: ABTrailsMobileTutorial = MOBILE_TUTORIALS_THIRD
    mobile_nodes: MobileNodes = MOBILE_NODES_THIRD
    name: str = "trail3"
    question: str = "Test"
    description: str = "trail3"
    device_type: str


class ABTrailsMobileFourthConfig(PublicModel):
    mobile_tutorials: ABTrailsMobileTutorial = MOBILE_TUTORIALS_FOURTH
    mobile_nodes: MobileNodes = MOBILE_NODES_FOURTH
    name: str = "trail4"
    question: str = "Test"
    description: str = "trail4"
    device_type: str


class NoneResponseType(str, Enum):
    TEXT = "text"
    MESSAGE = "message"
    TIMERANGE = "timeRange"
    GEOLOCATION = "geolocation"
    PHOTO = "photo"
    VIDEO = "video"
    DATE = "date"
    TIME = "time"
    FLANKER = "flanker"
    GYROSCOPEPRACTISE = "gyroscopePractise"
    GYROSCOPETEST = "gyroscopeTest"
    TOUCHPRACTISE = "touchPractise"
    TOUCHTEST = "touchTest"
    ABTRAILSTABLETFIRST = "ABTrailsTabletFirst"
    ABTRAILSTABLETSECOND = "ABTrailsTabletSecond"
    ABTRAILSTABLETTHIRD = "ABTrailsTabletThird"
    ABTRAILSTABLETFOURTH = "ABTrailsTabletFourth"
    ABTRAILSMOBILEFIRST = "ABTrailsMobileFirst"
    ABTRAILSMOBILESECOND = "ABTrailsMobileSecond"
    ABTRAILSMOBILETHIRD = "ABTrailsMobileThird"
    ABTRAILSMOBILEFOURTH = "ABTrailsMobileFourth"


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
    FLANKER = "flanker"
    GYROSCOPEPRACTISE = "gyroscopePractise"
    GYROSCOPETEST = "gyroscopeTest"
    TOUCHPRACTISE = "touchPractise"
    TOUCHTEST = "touchTest"
    ABTRAILSTABLETFIRST = "ABTrailsTabletFirst"
    ABTRAILSTABLETSECOND = "ABTrailsTabletSecond"
    ABTRAILSTABLETTHIRD = "ABTrailsTabletThird"
    ABTRAILSTABLETFOURTH = "ABTrailsTabletFourth"
    ABTRAILSMOBILEFIRST = "ABTrailsMobileFirst"
    ABTRAILSMOBILESECOND = "ABTrailsMobileSecond"
    ABTRAILSMOBILETHIRD = "ABTrailsMobileThird"
    ABTRAILSMOBILEFOURTH = "ABTrailsMobileFourth"


class PerformanceTaskType(str, Enum):
    FLANKER = "flanker"
    GYROSCOPE = "gyroscope"
    TOUCH = "touch"
    ABTRAILSTABLET = "ABTrailsTablet"
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
    FlankerConfig,
    GyroscopePractiseConfig,
    GyroscopeTestConfig,
    TouchPractiseConfig,
    TouchTestConfig,
    ABTrailsTabletFirstConfig,
    ABTrailsTabletSecondConfig,
    ABTrailsTabletThirdConfig,
    ABTrailsTabletFourthConfig,
    ABTrailsMobileFirstConfig,
    ABTrailsMobileSecondConfig,
    ABTrailsMobileThirdConfig,
    ABTrailsMobileFourthConfig,
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
    | FlankerConfig
    | GyroscopePractiseConfig
    | GyroscopeTestConfig
    | TouchPractiseConfig
    | TouchTestConfig
    # NOTE: Since, all Performance tasks has similar fields we should keep
    #       the flaxible data structure in oreder to provide correct
    #       Applet.from_orm usage()
    | dict
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
