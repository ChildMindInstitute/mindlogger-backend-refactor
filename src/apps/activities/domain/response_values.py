import uuid

from pydantic import Field, NonNegativeInt, root_validator, validator
from pydantic.color import Color

from apps.activities.errors import (
    InvalidDataMatrixByOptionError,
    InvalidDataMatrixError,
    InvalidScoreLengthError,
    InvalidUUIDError,
    MinValueError,
)
from apps.shared.domain import (
    PublicModel,
    validate_audio,
    validate_color,
    validate_image,
)


class TextValues(PublicModel):
    pass


class MessageValues(PublicModel):
    pass


class TimeRangeValues(PublicModel):
    pass


class TimeValues(PublicModel):
    pass


class GeolocationValues(PublicModel):
    pass


class PhotoValues(PublicModel):
    pass


class VideoValues(PublicModel):
    pass


class DateValues(PublicModel):
    pass


class FlankerValues(PublicModel):
    pass


class GyroscopeValues(PublicModel):
    pass


class TouchValues(PublicModel):
    pass


class ABTrailsIpadValues(PublicModel):
    pass


class ABTrailsMobileValues(PublicModel):
    pass


class _SingleSelectionValue(PublicModel):
    id: str | None = None
    text: str
    image: str | None
    score: int | None
    tooltip: str | None
    is_hidden: bool = Field(default=False)
    color: Color | None
    alert: str | None
    value: int | None

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
    palette_name: str | None
    options: list[_SingleSelectionValue]


class MultiSelectionValues(PublicModel):
    palette_name: str | None
    options: list[_SingleSelectionValue]


class SliderValueAlert(PublicModel):
    value: int | None = Field(
        default=0,
        description="Either value or min_value and max_value must be provided",
    )
    min_value: int | None
    max_value: int | None
    alert: str

    @root_validator()
    def validate_min_max_values(cls, values):
        if (
            values.get("min_value") is not None
            and values.get("max_value") is not None
        ):
            if values.get("min_value") >= values.get("max_value"):
                raise MinValueError()
        return values


class SliderValues(PublicModel):
    min_label: str | None = Field(..., max_length=20)
    max_label: str | None = Field(..., max_length=20)
    min_value: NonNegativeInt = Field(default=0, max_value=11)
    max_value: NonNegativeInt = Field(default=12, max_value=12)
    min_image: str | None
    max_image: str | None
    scores: list[int] | None
    alerts: list[SliderValueAlert] | None

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
        if values.get("scores") is not None:
            if (
                len(values.get("scores"))
                != values.get("max_value") - values.get("min_value") + 1
            ):
                raise InvalidScoreLengthError()
        return values


class NumberSelectionValues(PublicModel):
    min_value: NonNegativeInt = Field(default=0)
    max_value: NonNegativeInt = Field(default=100)

    @root_validator
    def validate_min_max(cls, values):
        if values.get("min_value") >= values.get("max_value"):
            raise MinValueError()
        return values


class DrawingValues(PublicModel):
    drawing_example: str | None
    drawing_background: str | None

    @validator("drawing_example", "drawing_background")
    def validate_image(cls, value):
        if value is not None:
            return validate_image(value)
        return value


class SliderRowsValue(SliderValues, PublicModel):
    id: str | None = None
    label: str = Field(..., max_length=11)

    @validator("id")
    def validate_id(cls, value):
        return validate_uuid(value)


class SliderRowsValues(PublicModel):
    rows: list[SliderRowsValue]


class _SingleSelectionOption(PublicModel):
    id: str | None = None
    text: str = Field(..., max_length=11)
    image: str | None
    tooltip: str | None

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
    row_name: str = Field(..., max_length=11)
    row_image: str | None
    tooltip: str | None

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
    score: int | None
    alert: str | None
    value: int | None


class _SingleSelectionDataRow(PublicModel):
    row_id: str
    options: list[_SingleSelectionDataOption]


class SingleSelectionRowsValues(PublicModel):
    rows: list[_SingleSelectionRow]
    options: list[_SingleSelectionOption]
    data_matrix: list[_SingleSelectionDataRow] | None

    @validator("data_matrix")
    def validate_data_matrix(cls, value, values):
        if value is not None:
            if len(value) != len(values["rows"]):
                raise InvalidDataMatrixError(
                    message="data_matrix must have the same length as rows"
                )
            for row in value:
                if len(row.options) != len(values["options"]):
                    raise InvalidDataMatrixByOptionError()
        return value


class MultiSelectionRowsValues(SingleSelectionRowsValues, PublicModel):
    pass


class AudioValues(PublicModel):
    max_duration: NonNegativeInt = 300


class AudioPlayerValues(PublicModel):
    file: str

    @validator("file")
    def validate_file(cls, value):
        return validate_audio(value)


ResponseValueConfigOptions = [
    TextValues,
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
    GyroscopeValues,
    TouchValues,
    ABTrailsIpadValues,
    ABTrailsMobileValues,
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
)


def validate_uuid(value):
    # if none, generate a new id
    if value is None:
        return str(uuid.uuid4())
    if not isinstance(value, str) or not uuid.UUID(value):
        raise InvalidUUIDError()
    return value
