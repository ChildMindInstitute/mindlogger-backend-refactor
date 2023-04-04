import uuid

from pydantic import (
    BaseModel,
    Field,
    NonNegativeInt,
    root_validator,
    validator,
)
from pydantic.color import Color

from apps.shared.domain import validate_audio, validate_color, validate_image


class TextValues(BaseModel):
    pass


class MessageValues(BaseModel):
    pass


class TimeRangeValues(BaseModel):
    pass


class GeolocationValues(BaseModel):
    pass


class PhotoValues(BaseModel):
    pass


class VideoValues(BaseModel):
    pass


class DateValues(BaseModel):
    pass


class _SingleSelectionValue(BaseModel):
    id: str | None = None
    text: str
    image: str | None
    score: int | None
    tooltip: str | None
    is_hidden: bool
    color: Color | None

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


class SingleSelectionValues(BaseModel):
    options: list[_SingleSelectionValue]


class MultiSelectionValues(BaseModel):
    options: list[_SingleSelectionValue]


class SliderValues(BaseModel):
    min_label: str | None = Field(..., max_length=20)
    max_label: str | None = Field(..., max_length=20)
    min_value: NonNegativeInt = Field(default=0, max_value=11)
    max_value: NonNegativeInt = Field(default=12, max_value=12)
    min_image: str | None
    max_image: str | None
    scores: list[int] | None

    @validator("min_image", "max_image")
    def validate_image(cls, value):
        if value is not None:
            return validate_image(value)
        return value

    @root_validator
    def validate_min_max(cls, values):
        if values.get("min_value") >= values.get("max_value"):
            raise ValueError("min_value must be less than max_value")
        return values

    @root_validator
    def validate_scores(cls, values):
        if values.get("scores") is not None:
            if (
                len(values.get("scores"))
                != values.get("max_value") - values.get("min_value") + 1
            ):
                raise ValueError(
                    "scores must have the same length as the range of min_value and max_value"  # noqa: E501
                )
        return values


class NumberSelectionValues(BaseModel):
    min_value: NonNegativeInt = Field(default=0)
    max_value: NonNegativeInt = Field(default=100)

    @root_validator
    def validate_min_max(cls, values):
        if values.get("min_value") >= values.get("max_value"):
            raise ValueError("min_value must be less than max_value")
        return values


class DrawingValues(BaseModel):
    drawing_example: str | None
    drawing_background: str | None

    @validator("drawing_example", "drawing_background")
    def validate_image(cls, value):
        if value is not None:
            return validate_image(value)
        return value


class SliderRowsValue(SliderValues, BaseModel):
    id: str | None = None
    label: str = Field(..., max_length=11)

    @validator("id")
    def validate_id(cls, value):
        return validate_uuid(value)


class SliderRowsValues(BaseModel):
    rows: list[SliderRowsValue]


class _SingleSelectionRowValue(BaseModel):
    id: str | None = None
    text: str = Field(..., max_length=11)
    image: str | None
    score: int | None
    tooltip: str | None

    @validator("image")
    def validate_image(cls, value):
        if value is not None:
            return validate_image(value)
        return value

    @validator("id")
    def validate_id(cls, value):
        return validate_uuid(value)


class _SingleSelectionRowsValue(BaseModel):
    id: str | None = None
    row_name: str = Field(..., max_length=11)
    row_image: str | None
    tooltip: str | None
    options: list[_SingleSelectionRowValue]

    @validator("row_image")
    def validate_image(cls, value):
        if value is not None:
            return validate_image(value)
        return value

    @validator("id")
    def validate_id(cls, value):
        return validate_uuid(value)


class SingleSelectionRowsValues(BaseModel):
    rows: list[_SingleSelectionRowsValue]


class MultiSelectionRowsValues(SingleSelectionRowsValues, BaseModel):
    pass


class AudioValues(BaseModel):
    max_duration: NonNegativeInt = 300


class AudioPlayerValues(BaseModel):
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
)


def validate_uuid(value):
    # if none, generate a new id
    if value is None:
        return str(uuid.uuid4())
    if not isinstance(value, str) or not uuid.UUID(value):
        raise ValueError("id must be a valid uuid")
    return value
