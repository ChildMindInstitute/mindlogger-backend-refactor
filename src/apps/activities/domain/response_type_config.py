from enum import StrEnum
from typing import Literal

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
    ABTrailsNodes,
    ABTrailsTutorial,
)

# from apps.activities.domain.response_values import ResponseValueConfigOptions
from apps.activities.errors import CorrectAnswerRequiredError
from apps.shared.domain import PublicModel


class ResponseType(StrEnum):
    TEXT = "text"
    PARAGRAPHTEXT = "paragraphText"
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
    UNITY = "unity"
    PHRASAL_TEMPLATE = "phrasalTemplate"
    REQUEST_HEALTH_RECORD_DATA = "requestHealthRecordData"

    @classmethod
    def get_non_response_types(cls):
        return (
            cls.TEXT,
            cls.PARAGRAPHTEXT,
            cls.MESSAGE,
            cls.TIMERANGE,
            cls.GEOLOCATION,
            cls.PHOTO,
            cls.VIDEO,
            cls.DATE,
            cls.TIME,
            cls.FLANKER,
            cls.STABILITYTRACKER,
            cls.ABTRAILS,
            cls.UNITY,
        )

    @classmethod
    def conditional_logic_types(cls):
        return (
            cls.DATE,
            cls.NUMBERSELECT,
            cls.TIME,
            cls.TIMERANGE,
            cls.SINGLESELECTROWS,
            cls.MULTISELECTROWS,
            cls.SLIDERROWS,
            cls.SINGLESELECT,
            cls.MULTISELECT,
            cls.SLIDER,
        )

    @classmethod
    def options_mapped_on_value(cls) -> list[str]:
        return [
            cls.SINGLESELECT,
            cls.MULTISELECT,
        ]

    @classmethod
    def options_mapped_on_id(cls) -> list[str]:
        return [
            cls.SINGLESELECTROWS,
            cls.MULTISELECTROWS,
        ]

    @classmethod
    def option_based(cls) -> list[str]:
        return cls.options_mapped_on_id() + cls.options_mapped_on_value()


class AdditionalResponseOption(PublicModel):
    text_input_option: bool
    text_input_required: bool


class _ScreenConfig(PublicModel):
    remove_back_button: bool
    skippable_item: bool


class TextConfig(_ScreenConfig):
    type: Literal[ResponseType.TEXT] | None
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


class ParagraphTextConfig(_ScreenConfig):
    type: Literal[ResponseType.PARAGRAPHTEXT] | None
    max_response_length: PositiveInt = 1000
    response_required: bool


class _SelectionConfig(_ScreenConfig):
    randomize_options: bool
    timer: NonNegativeInt | None
    add_scores: bool
    set_alerts: bool
    add_tooltip: bool
    set_palette: bool
    add_tokens: bool | None
    additional_response_option: AdditionalResponseOption
    portrait_layout: bool | None


class SingleSelectionConfig(_SelectionConfig, PublicModel):
    type: Literal[ResponseType.SINGLESELECT] | None
    auto_advance: bool = False
    response_data_identifier: bool = False


class MultiSelectionConfig(_SelectionConfig, PublicModel):
    type: Literal[ResponseType.MULTISELECT] | None


class MessageConfig(PublicModel):
    type: Literal[ResponseType.MESSAGE] | None
    remove_back_button: bool
    timer: NonNegativeInt | None


class SliderConfig(_ScreenConfig):
    type: Literal[ResponseType.SLIDER] | None
    add_scores: bool
    set_alerts: bool
    additional_response_option: AdditionalResponseOption
    show_tick_marks: bool
    show_tick_labels: bool
    continuous_slider: bool
    timer: NonNegativeInt | None


class NumberSelectionConfig(_ScreenConfig):
    type: Literal[ResponseType.NUMBERSELECT] | None
    additional_response_option: AdditionalResponseOption


class DefaultConfig(_ScreenConfig):
    additional_response_option: AdditionalResponseOption
    timer: NonNegativeInt | None


class TimeRangeConfig(DefaultConfig, PublicModel):
    type: Literal[ResponseType.TIMERANGE] | None


class TimeConfig(DefaultConfig, PublicModel):
    type: Literal[ResponseType.TIME] | None


class GeolocationConfig(DefaultConfig, PublicModel):
    type: Literal[ResponseType.GEOLOCATION] | None


class DrawingConfig(_ScreenConfig):
    type: Literal[ResponseType.DRAWING] | None
    additional_response_option: AdditionalResponseOption
    timer: NonNegativeInt | None
    remove_undo_button: bool = False
    navigation_to_top: bool = False


class PhotoConfig(DefaultConfig, PublicModel):
    type: Literal[ResponseType.PHOTO] | None


class VideoConfig(DefaultConfig, PublicModel):
    type: Literal[ResponseType.VIDEO] | None


class DateConfig(DefaultConfig, PublicModel):
    type: Literal[ResponseType.DATE] | None


class SliderRowsConfig(_ScreenConfig):
    type: Literal[ResponseType.SLIDERROWS] | None
    add_scores: bool
    set_alerts: bool
    timer: NonNegativeInt | None


class SingleSelectionRowsConfig(_ScreenConfig):
    type: Literal[ResponseType.SINGLESELECTROWS] | None
    timer: NonNegativeInt | None
    add_scores: bool
    set_alerts: bool
    add_tooltip: bool
    add_tokens: bool | None


class MultiSelectionRowsConfig(SingleSelectionRowsConfig, PublicModel):
    type: Literal[ResponseType.MULTISELECTROWS] | None  # type: ignore[assignment]


class AudioConfig(DefaultConfig, PublicModel):
    type: Literal[ResponseType.AUDIO] | None


class AudioPlayerConfig(_ScreenConfig):
    type: Literal[ResponseType.AUDIOPLAYER] | None
    additional_response_option: AdditionalResponseOption
    play_once: bool


class PhrasalTemplateConfig(PublicModel):
    type: Literal[ResponseType.PHRASAL_TEMPLATE] | None
    remove_back_button: bool


class RequestHealthRecordDataConfig(_ScreenConfig):
    type: Literal[ResponseType.REQUEST_HEALTH_RECORD_DATA] | None
    skippable_item: bool = False


class UnityConfig(PublicModel):
    type: Literal[ResponseType.UNITY] | None
    device_type: str | None
    file: str | None


class InputType(StrEnum):
    GYROSCOPE = "gyroscope"
    TOUCH = "touch"


class Phase(StrEnum):
    PRACTICE = "practice"
    TEST = "test"


class StabilityTrackerConfig(PublicModel):
    type: Literal[ResponseType.STABILITYTRACKER] | None
    user_input_type: InputType | None
    phase: Phase
    trials_number: int = 0
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
    text: str | None = None  # name
    value: int | None = None
    weight: int | None = None


class BlockConfiguration(PublicModel):
    name: str
    order: list[StimulusConfigId]


class SamplingMethod(StrEnum):
    RANDOMIZE_ORDER = "randomize-order"
    FIXED_ORDER = "fixed-order"


class BlockType(StrEnum):
    TEST = "test"
    PRACTICE = "practice"


class ButtonConfiguration(PublicModel):
    text: str | None = None  # name
    image: str | None = None
    value: int | None = None


class FixationScreen(PublicModel):
    value: str | None = None
    image: str | None = None


class FlankerConfig(PublicModel):
    type: Literal[ResponseType.FLANKER] | None
    stimulus_trials: list[StimulusConfiguration]
    blocks: list[BlockConfiguration]
    buttons: list[ButtonConfiguration]
    next_button: str | None = None
    fixation_duration: int | None = None
    fixation_screen: FixationScreen | None = None
    minimum_accuracy: int | None = None
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


class ABTrailsOrder(StrEnum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"
    FOURTH = "fourth"


class ABTrailsDeviceType(StrEnum):
    TABLET = "tablet"
    MOBILE = "mobile"


class ABTrailsConfig(PublicModel):
    type: Literal[ResponseType.ABTRAILS] | None
    device_type: ABTrailsDeviceType | None
    order_name: ABTrailsOrder
    tutorials: ABTrailsTutorial | None = None
    nodes: ABTrailsNodes | None = None

    # HACK: Remember that values get into this validator only because
    #       of class attributes ordering. Using root_validator over it
    #       might be preferable since it is more transparent.
    #       This approach is used in order to follow the consistency.
    @validator("tutorials", pre=True)
    def validate_tutorials(cls, value, values) -> ABTrailsTutorial | None:
        if values.get("device_type") == ABTrailsDeviceType.TABLET:
            if values.get("order_name") == ABTrailsOrder.FIRST:
                return TABLET_TUTORIALS_FIRST
            if values.get("order_name") == ABTrailsOrder.SECOND:
                return TABLET_TUTORIALS_SECOND
            if values.get("order_name") == ABTrailsOrder.THIRD:
                return TABLET_TUTORIALS_THIRD
            if values.get("order_name") == ABTrailsOrder.FOURTH:
                return TABLET_TUTORIALS_FOURTH

        if values.get("device_type") == ABTrailsDeviceType.MOBILE:
            if values.get("order_name") == ABTrailsOrder.FIRST:
                return MOBILE_TUTORIALS_FIRST
            if values.get("order_name") == ABTrailsOrder.SECOND:
                return MOBILE_TUTORIALS_SECOND
            if values.get("order_name") == ABTrailsOrder.THIRD:
                return MOBILE_TUTORIALS_THIRD
            if values.get("order_name") == ABTrailsOrder.FOURTH:
                return MOBILE_TUTORIALS_FOURTH

        return value

    @validator("nodes", pre=True)
    def validate_nodes(cls, value, values) -> ABTrailsNodes | None:
        if values.get("device_type") == ABTrailsDeviceType.TABLET:
            if values.get("order_name") == ABTrailsOrder.FIRST:
                return TABLET_NODES_FIRST
            if values.get("order_name") == ABTrailsOrder.SECOND:
                return TABLET_NODES_SECOND
            if values.get("order_name") == ABTrailsOrder.THIRD:
                return TABLET_NODES_THIRD
            if values.get("order_name") == ABTrailsOrder.FOURTH:
                return TABLET_NODES_FOURTH

        if values.get("device_type") == ABTrailsDeviceType.MOBILE:
            if values.get("order_name") == ABTrailsOrder.FIRST:
                return MOBILE_NODES_FIRST
            if values.get("order_name") == ABTrailsOrder.SECOND:
                return MOBILE_NODES_SECOND
            if values.get("order_name") == ABTrailsOrder.THIRD:
                return MOBILE_NODES_THIRD
            if values.get("order_name") == ABTrailsOrder.FOURTH:
                return MOBILE_NODES_FOURTH

        return value


class PerformanceTaskType(StrEnum):
    FLANKER = "flanker"
    GYROSCOPE = "gyroscope"
    TOUCH = "touch"
    ABTRAILS = "ABTrails"
    UNITY = "unity"

    @classmethod
    def get_values(cls) -> list[str]:
        return [i.value for i in cls]


ResponseTypeConfig = (
    TextConfig
    | ParagraphTextConfig
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
    | ABTrailsConfig
    | PhrasalTemplateConfig
    | UnityConfig
    | RequestHealthRecordDataConfig
)
