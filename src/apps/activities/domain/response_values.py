import uuid
from enum import Enum
from pydantic import Field, NonNegativeInt, root_validator, validator
from pydantic.color import Color

from apps.shared.domain import (
    InternalModel,
    validate_audio,
    validate_color,
    validate_image,
)


TextValues = None
MessageValues = None
TimeRangeValues = None
GeolocationValues = None
PhotoValues = None
VideoValues = None
DateValues = None


class _SingleSelectionValue(InternalModel):
    id: uuid.UUID
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


class MultiSelectionValues(SingleSelectionValues, InternalModel):
    pass


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


class NumberSelectionValues(InternalModel):
    min_value: NonNegativeInt = Field(default=0)
    max_value: NonNegativeInt = Field(default=100)

    @root_validator
    def validate_min_max(cls, values):
        if values.get("min_value") >= values.get("max_value"):
            raise ValueError("min_value must be less than max_value")
        return values


class DrawingValues(InternalModel):
    drawing_example: str
    drawing_background: str

    @validator("drawing_example", "drawing_background")
    def validate_image(cls, value):
        return validate_image(value)


class SliderRowsValue(SliderValues, InternalModel):
    id: uuid.UUID
    label: str = Field(..., max_length=11)


class SliderRowsValues(InternalModel):
    rows: list[SliderRowsValue]


class _SingleSelectionRowValue(InternalModel):
    id: uuid.UUID
    text: str
    image: str
    score: int
    tooltip: str

    @validator("image")
    def validate_image(cls, value):
        return validate_image(value)


class _SingleSelectionRowsValue(InternalModel):
    id: uuid.UUID
    row_name: str
    row_image: str
    tooltip: str
    options: list[_SingleSelectionRowValue]

    @validator("row_image")
    def validate_image(cls, value):
        return validate_image(value)


class SingleSelectionRowsValues(InternalModel):
    rows: list[_SingleSelectionRowsValue]


class MultiSelectionRowsValues(SingleSelectionRowsValues, InternalModel):
    pass


class AudioValues(InternalModel):
    max_duration: NonNegativeInt = 300


class AudioPlayerValues(InternalModel):
    file: str

    @validator("file")
    def validate_file(cls, value):
        return validate_audio(value)


ResponseValueConfigOptions = [
    TextValues,
    SingleSelectionValues,
    MultiSelectionValues,
    MessageValues,
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
]


ResponseValueConfig = (
    TextValues
    | SingleSelectionValues
    | MultiSelectionValues
    | MessageValues
    | SliderValues
    | NumberSelectionValues
    | TimeRangeValues
    | GeolocationValues
    | DrawingValues
    | PhotoValues
    | VideoValues
    | DateValues
    | SliderRowsValues
    | SingleSelectionRowsValues
    | MultiSelectionRowsValues
    | AudioValues
    | AudioPlayerValues
)
