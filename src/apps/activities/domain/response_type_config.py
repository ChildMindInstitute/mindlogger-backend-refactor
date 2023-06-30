from enum import Enum

from pydantic import (
    Field,
    NonNegativeInt,
    PositiveInt,
    root_validator,
    validator,
)

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


class InputType(str, Enum):
    GYROSCOPE = "gyroscope"
    TOUCH = "touch"


class Phase(str, Enum):
    PRACTICE = "practice"
    TEST = "test"


class StabilityTrackerConfig(PublicModel):
    user_input_type: InputType
    phase: Phase
    trials_number: int
    duration_minutes: float
    lambda_slope: float
    max_off_target_time: int = 10
    num_test_trials: int = 10
    task_mode: str = "pseudo_stair"
    tracking_dims: int = 2
    show_score: bool = True
    basis_func: str = "zeros_1d"
    noise_level: float = 0
    task_loop_rate: float = 0.0167
    cycles_per_min: float = 2
    oob_duration: float = 0.2
    initial_lambda: float = 0.075
    show_preview: bool = True
    num_preview_stim: int = 0
    preview_step_gap: int = 100
    dimension_count: int = 1
    max_rad: float = 0.26167


class StimulusConfigId(str):
    pass


class StimulusConfiguration(PublicModel):
    id: StimulusConfigId
    image: str | None
    text: str  # name
    value: int | None
    weight: int | None


class BlockConfiguration(PublicModel):
    name: str
    order: list[StimulusConfigId]


class SamplingMethod(str, Enum):
    RANDOMIZE_ORDER = "randomize-order"
    FIXED_ORDER = "fixed-order"


class BlockType(str, Enum):
    TEST = "test"
    PRACTICE = "practice"


class ButtonConfiguration(PublicModel):
    text: str  # name
    image: str | None
    value: int


class FixationScreen(PublicModel):
    value: str
    image: str


class FlankerConfig(PublicModel):
    stimulus_trials: list[StimulusConfiguration]
    blocks: list[BlockConfiguration]
    buttons: list[ButtonConfiguration]
    next_button: str
    fixation_duration: int
    fixation_screen: FixationScreen
    minimum_accuracy: int
    sample_size: int = 1
    sampling_method: SamplingMethod
    show_feedback: bool
    show_fixation: bool
    show_results: bool
    trial_duration: int
    is_last_practice: bool
    is_first_practice: bool
    is_last_test: bool
    block_type: BlockType


class ABTrailsOrder(str, Enum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    FOURTH = "fourth"


class ABTrailsDeviceType(str, Enum):
    TABLET = "tablet"
    MOBILE = "mobile"


# TODO: For ABTrails - Make one type of activity instead of eight
#  this type must include all fields for Tablet and Mobile as in the example:
#   radius: float;
#   font_size: float;
#   font_size_begin_end: float | None;
#   begin_word_length: float | None;
#   end_word_length: float | None;
class ABTrailsConfig(PublicModel):
    device_type: ABTrailsDeviceType
    order_name: ABTrailsOrder
    tablet_tutorials: ABTrailsTabletTutorial | None = None
    tablet_nodes: TabletNodes = TABLET_NODES_FIRST

    # HACK: Remember that values get into this validator only because
    #       of class attributes ordering. Using root_validator over it
    #       might be preferable since it is more transparent.
    #       This approach is used in order to follow the consistancy.
    @validator("tablet_tutorials", pre=True)
    def validate_type_and_phase(
        cls, value, values
    ) -> ABTrailsTabletTutorial | None:
        if (
            values.get("device_type") == ABTrailsDeviceType.TABLET
            and values.get("order_name") == ABTrailsOrder.FIRST
        ):
            return TABLET_TUTORIALS_FIRST
        if (
            values.get("device_type") == ABTrailsDeviceType.TABLET
            and values.get("order_name") == ABTrailsOrder.SECOND
        ):
            return TABLET_TUTORIALS_SECOND

        return value


# class ABTrailsTabletSecondConfig(PublicModel):
#     tablet_tutorials: ABTrailsTabletTutorial = TABLET_TUTORIALS_SECOND
#     tablet_nodes: TabletNodes = TABLET_NODES_SECOND
#     name: str = "trail2"
#     question: str = "Test"
#     description: str = "trail2"
#     device_type: str
#
#
# class ABTrailsTabletThirdConfig(PublicModel):
#     tablet_tutorials: ABTrailsTabletTutorial = TABLET_TUTORIALS_THIRD
#     tablet_nodes: TabletNodes = TABLET_NODES_THIRD
#     name: str = "trail3"
#     question: str = "Test"
#     description: str = "trail3"
#     device_type: str
#
#
# class ABTrailsTabletFourthConfig(PublicModel):
#     tablet_tutorials: ABTrailsTabletTutorial = TABLET_TUTORIALS_FOURTH
#     tablet_nodes: TabletNodes = TABLET_NODES_FOURTH
#     name: str = "trail4"
#     question: str = "Test"
#     description: str = "trail4"
#     device_type: str
#
#
# class ABTrailsMobileFirstConfig(PublicModel):
#     mobile_tutorials: ABTrailsMobileTutorial = MOBILE_TUTORIALS_FIRST
#     mobile_nodes: MobileNodes = MOBILE_NODES_FIRST
#     name: str = "trail1"
#     question: str = "Test"
#     description: str = "trail1"
#     device_type: str
#
#
# class ABTrailsMobileSecondConfig(PublicModel):
#     mobile_tutorials: ABTrailsMobileTutorial = MOBILE_TUTORIALS_SECOND
#     mobile_nodes: MobileNodes = MOBILE_NODES_SECOND
#     name: str = "trail2"
#     question: str = "Test"
#     description: str = "trail2"
#     device_type: str
#
#
# class ABTrailsMobileThirdConfig(PublicModel):
#     mobile_tutorials: ABTrailsMobileTutorial = MOBILE_TUTORIALS_THIRD
#     mobile_nodes: MobileNodes = MOBILE_NODES_THIRD
#     name: str = "trail3"
#     question: str = "Test"
#     description: str = "trail3"
#     device_type: str
#
#
# class ABTrailsMobileFourthConfig(PublicModel):
#     mobile_tutorials: ABTrailsMobileTutorial = MOBILE_TUTORIALS_FOURTH
#     mobile_nodes: MobileNodes = MOBILE_NODES_FOURTH
#     name: str = "trail4"
#     question: str = "Test"
#     description: str = "trail4"
#     device_type: str


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
    STABILITYTRACKER = "stabilityTracker"
    ABTRAILS = "ABTrails"
    # ABTRAILSTABLETSECOND = "ABTrailsTabletSecond"
    # ABTRAILSTABLETTHIRD = "ABTrailsTabletThird"
    # ABTRAILSTABLETFOURTH = "ABTrailsTabletFourth"
    # ABTRAILSMOBILEFIRST = "ABTrailsMobileFirst"
    # ABTRAILSMOBILESECOND = "ABTrailsMobileSecond"
    # ABTRAILSMOBILETHIRD = "ABTrailsMobileThird"
    # ABTRAILSMOBILEFOURTH = "ABTrailsMobileFourth"


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
    STABILITYTRACKER = "stabilityTracker"
    ABTRAILS = "ABTrails"
    # ABTRAILSTABLETSECOND = "ABTrailsTabletSecond"
    # ABTRAILSTABLETTHIRD = "ABTrailsTabletThird"
    # ABTRAILSTABLETFOURTH = "ABTrailsTabletFourth"
    # ABTRAILSMOBILEFIRST = "ABTrailsMobileFirst"
    # ABTRAILSMOBILESECOND = "ABTrailsMobileSecond"
    # ABTRAILSMOBILETHIRD = "ABTrailsMobileThird"
    # ABTRAILSMOBILEFOURTH = "ABTrailsMobileFourth"


class PerformanceTaskType(str, Enum):
    FLANKER = "flanker"
    STABILITYTRACKER = "stabilityTracker"
    ABTRAILS = "ABTrails"
    # ABTRAILSMOBILE = "ABTrailsMobile"


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
    StabilityTrackerConfig,
    ABTrailsConfig,
    # ABTrailsTabletSecondConfig,
    # ABTrailsTabletThirdConfig,
    # ABTrailsTabletFourthConfig,
    # ABTrailsMobileFirstConfig,
    # ABTrailsMobileSecondConfig,
    # ABTrailsMobileThirdConfig,
    # ABTrailsMobileFourthConfig,
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
    | StabilityTrackerConfig
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
