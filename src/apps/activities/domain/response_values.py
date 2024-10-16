from enum import StrEnum
from typing import Literal

from pydantic import Field, NonNegativeInt, root_validator, validator
from pydantic.color import Color

from apps.activities.domain.response_type_config import (
    ABTrailsConfig,
    AudioConfig,
    AudioPlayerConfig,
    DateConfig,
    DrawingConfig,
    FlankerConfig,
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
    StabilityTrackerConfig,
    TextConfig,
    TimeConfig,
    TimeRangeConfig,
    UnityConfig,
    VideoConfig,
)
from apps.activities.errors import (
    InvalidDataMatrixByOptionError,
    InvalidDataMatrixError,
    InvalidScoreLengthError,
    MinValueError,
    MultiSelectNoneOptionError,
)
from apps.shared.domain import PublicModel, validate_color, validate_image, validate_uuid


class PhrasalTemplateFieldType(StrEnum):
    SENTENCE = "sentence"
    ITEM_RESPONSE = "item_response"
    LINE_BREAK = "line_break"


class PhrasalTemplateDisplayMode(StrEnum):
    BULLET_LIST = "bullet_list"
    SENTENCE = "sentence"
    BULLET_LIST_OPTION_ROW = "bullet_list_option_row"
    BULLET_LIST_ROW_OPTION = "bullet_list_text_row"
    SENTENCE_OPTION_ROW = "sentence_option_row"
    SENTENCE_ROW_OPTION = "sentence_row_option"


class TextValues(PublicModel):
    type: Literal[ResponseType.TEXT] | None


class ParagraphTextValues(PublicModel):
    type: Literal[ResponseType.PARAGRAPHTEXT] | None


class MessageValues(PublicModel):
    type: Literal[ResponseType.MESSAGE] | None


class TimeRangeValues(PublicModel):
    type: Literal[ResponseType.TIMERANGE] | None


class TimeValues(PublicModel):
    type: Literal[ResponseType.TIME] | None


class GeolocationValues(PublicModel):
    type: Literal[ResponseType.GEOLOCATION] | None


class PhotoValues(PublicModel):
    type: Literal[ResponseType.PHOTO] | None


class VideoValues(PublicModel):
    type: Literal[ResponseType.VIDEO] | None


class DateValues(PublicModel):
    type: Literal[ResponseType.DATE] | None


class FlankerValues(PublicModel):
    type: Literal[ResponseType.FLANKER] | None


class StabilityTrackerValues(PublicModel):
    type: Literal[ResponseType.STABILITYTRACKER] | None


class ABTrailsValues(PublicModel):
    type: Literal[ResponseType.ABTRAILS] | None


class UnityValues(PublicModel):
    type: Literal[ResponseType.UNITY] | None


class _SingleSelectionValue(PublicModel):
    id: str | None = None
    text: str
    image: str | None = None
    score: float | None = None
    tooltip: str | None = None
    is_hidden: bool = Field(default=False)
    color: Color | None = None
    alert: str | None = None
    value: int | None = None

    @validator("score")
    def validate_score(cls, value):
        # validate score value to be 2 decimals max
        if value:
            return round(value, 2)
        return value

    @validator("image")
    def validate_image(cls, value):
        # validate image if not None
        if value is not None:
            return validate_image(value)
        return value

    @validator("color")
    def validate_color(cls, value):
        if value is not None:
            return validate_color(value)
        return value

    @validator("id")
    def validate_id(cls, value):
        return validate_uuid(value)


class SingleSelectionValues(PublicModel):
    type: Literal[ResponseType.SINGLESELECT] | None
    palette_name: str | None
    options: list[_SingleSelectionValue]

    @validator("options")
    def validate_options(cls, value):
        return validate_options_value(value)


class _MultiSelectionValue(_SingleSelectionValue):
    is_none_above: bool = Field(default=False)


class MultiSelectionValues(PublicModel):
    type: Literal[ResponseType.MULTISELECT] | None
    palette_name: str | None
    options: list[_MultiSelectionValue]

    @validator("options")
    def validate_options(cls, value):
        return validate_options_value(value)

    @validator("options")
    def validate_none_option_flag(cls, value):
        return validate_none_option_flag(value)


class SliderValueAlert(PublicModel):
    value: int | None = Field(
        default=0,
        description="Either value or min_value and max_value must be provided. For SliderRows, only value is allowed.",  # noqa: E501
    )
    min_value: int | None
    max_value: int | None
    alert: str

    @root_validator()
    def validate_min_max_values(cls, values):
        if values.get("min_value") is not None and values.get("max_value") is not None:
            if values.get("min_value") >= values.get("max_value"):
                raise MinValueError()
        return values


class SliderValuesBase(PublicModel):
    min_label: str | None = Field(..., max_length=100)
    max_label: str | None = Field(..., max_length=100)
    min_value: NonNegativeInt = Field(default=0, max_value=11)
    max_value: NonNegativeInt = Field(default=12, max_value=12)
    min_image: str | None = None
    max_image: str | None = None
    scores: list[float] | None = None
    alerts: list[SliderValueAlert] | None = None

    @validator("scores")
    def validate_score(cls, value):
        # validate each score values to be 2 decimals max
        if value:
            value = [round(score, 2) for score in value]
        return value

    @validator("min_image", "max_image")
    def validate_image(cls, value):
        if value is not None:
            return validate_image(value)
        return value

    @root_validator
    def validate_min_max(cls, values):
        if values.get("min_value") >= values.get("max_value"):
            raise MinValueError()
        return values

    @root_validator
    def validate_scores(cls, values):
        # length of scores must be equal to max_value - min_value + 1
        scores = values.get("scores", [])
        if scores:
            if len(scores) != values.get("max_value") - values.get("min_value") + 1:
                raise InvalidScoreLengthError()
        return values


class SliderValues(SliderValuesBase):
    type: Literal[ResponseType.SLIDER] | None


class NumberSelectionValues(PublicModel):
    type: Literal[ResponseType.NUMBERSELECT] | None
    min_value: NonNegativeInt = Field(default=0)
    max_value: NonNegativeInt = Field(default=100)

    @root_validator
    def validate_min_max(cls, values):
        if values.get("min_value") >= values.get("max_value"):
            raise MinValueError()
        return values


class DrawingProportion(PublicModel):
    enabled: bool


class DrawingValues(PublicModel):
    type: Literal[ResponseType.DRAWING] | None
    drawing_example: str | None
    drawing_background: str | None
    proportion: DrawingProportion | None = None

    @validator("drawing_example", "drawing_background")
    def validate_image(cls, value):
        if value is not None:
            return validate_image(value)
        return value


class SliderRowsValue(SliderValuesBase, PublicModel):
    id: str | None = None
    label: str = Field(..., max_length=100)

    @validator("id")
    def validate_id(cls, value):
        return validate_uuid(value)


class SliderRowsValues(PublicModel):
    type: Literal[ResponseType.SLIDERROWS] | None
    rows: list[SliderRowsValue]


class _SingleSelectionOption(PublicModel):
    id: str | None = None
    text: str = Field(..., max_length=100)
    image: str | None = None
    tooltip: str | None = None

    @validator("image")
    def validate_image(cls, value):
        if value is not None:
            return validate_image(value)
        return value

    @validator("id")
    def validate_id(cls, value):
        return validate_uuid(value)


class _SingleSelectionRow(PublicModel):
    id: str | None = None
    row_name: str = Field(..., max_length=100)
    row_image: str | None = None
    tooltip: str | None = None

    @validator("row_image")
    def validate_image(cls, value):
        if value is not None:
            return validate_image(value)
        return value

    @validator("id")
    def validate_id(cls, value):
        return validate_uuid(value)


class _SingleSelectionDataOption(PublicModel):
    option_id: str
    score: int | None = None
    alert: str | None = None
    value: int | None = None


class _SingleSelectionDataRow(PublicModel):
    row_id: str
    options: list[_SingleSelectionDataOption]

    @validator("options")
    def validate_options(cls, value):
        return validate_options_value(value)


class SingleSelectionRowsValues(PublicModel):
    type: Literal[ResponseType.SINGLESELECTROWS] | None
    rows: list[_SingleSelectionRow]
    options: list[_SingleSelectionOption]
    data_matrix: list[_SingleSelectionDataRow] | None = None

    @validator("data_matrix")
    def validate_data_matrix(cls, value, values):
        if value is not None:
            if len(value) != len(values["rows"]):
                raise InvalidDataMatrixError()
            for row in value:
                if len(row.options) != len(values["options"]):
                    raise InvalidDataMatrixByOptionError()
        return value


class MultiSelectionRowsValues(SingleSelectionRowsValues, PublicModel):
    type: Literal[ResponseType.MULTISELECTROWS] | None  # type: ignore[assignment]


class AudioValues(PublicModel):
    type: Literal[ResponseType.AUDIO] | None
    max_duration: NonNegativeInt = 300


class AudioPlayerValues(PublicModel):
    type: Literal[ResponseType.AUDIOPLAYER] | None
    file: str | None = Field(default=None)


class _PhrasalTemplateSentenceField(PublicModel):
    type: PhrasalTemplateFieldType = PhrasalTemplateFieldType.SENTENCE
    text: str


class _PhrasalTemplateItemResponseField(PublicModel):
    type: PhrasalTemplateFieldType = PhrasalTemplateFieldType.ITEM_RESPONSE
    item_name: str
    display_mode: PhrasalTemplateDisplayMode
    item_index: int | None = None


class _PhrasalTemplateLineBreakField(PublicModel):
    type: PhrasalTemplateFieldType = PhrasalTemplateFieldType.LINE_BREAK


PhrasalTemplateField = (
    _PhrasalTemplateSentenceField | _PhrasalTemplateItemResponseField | _PhrasalTemplateLineBreakField
)


class PhrasalTemplatePhrase(PublicModel):
    image: str | None = Field(default=None)
    fields: list[PhrasalTemplateField]


class PhrasalTemplateValues(PublicModel):
    type: Literal[ResponseType.PHRASAL_TEMPLATE] | None
    card_title: str
    phrases: list[PhrasalTemplatePhrase]


ResponseValueConfigOptions = [
    TextValues,
    ParagraphTextValues,
    SingleSelectionValues,
    MultiSelectionValues,
    SliderValues,
    NumberSelectionValues,
    TimeRangeValues,
    GeolocationValues,
    DrawingValues,
    PhotoValues,
    VideoValues,
    DateValues,
    SliderRowsValues,
    SingleSelectionRowsValues,
    MultiSelectionRowsValues,
    AudioValues,
    AudioPlayerValues,
    MessageValues,
    TimeValues,
    FlankerValues,
    StabilityTrackerValues,
    ABTrailsValues,
    UnityValues,
    PhrasalTemplateValues,
]


ResponseValueConfig = (
    SingleSelectionValues
    | MultiSelectionValues
    | SliderValues
    | NumberSelectionValues
    | DrawingValues
    | SliderRowsValues
    | SingleSelectionRowsValues
    | MultiSelectionRowsValues
    | AudioValues
    | AudioPlayerValues
    | TimeValues
    | UnityValues
    | PhrasalTemplateValues
)


def validate_options_value(options):
    # if value inside options is None, set it to max_value + 1
    for option in options:
        if option.value is None:
            option.value = (
                max(
                    [option.value if option.value is not None else -1 for option in options],
                    default=-1,
                )
                + 1
            )

    return options


def validate_none_option_flag(options):
    none_option_counter = 0

    for option in options:
        if option.is_none_above:
            none_option_counter += 1

    if none_option_counter > 1:
        raise MultiSelectNoneOptionError()

    return options


ResponseTypeConfigOptions = [
    TextConfig,
    ParagraphTextConfig,
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
    UnityConfig,
    PhrasalTemplateConfig,
]

ResponseTypeValueConfig = {}
index = 0

for response_type in ResponseType:
    zipped_type_value = list(zip(ResponseValueConfigOptions, ResponseTypeConfigOptions))

    ResponseTypeValueConfig[response_type] = {
        "config": zipped_type_value[index][1],
        "value": zipped_type_value[index][0],
    }
    index += 1
