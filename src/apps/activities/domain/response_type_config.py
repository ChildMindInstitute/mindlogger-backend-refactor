from enum import Enum

from pydantic import validator
from pydantic.color import Color

from apps.shared.domain import InternalModel, validate_color, validate_image


class TextConfig(InternalModel):
    max_response_length: int = -1
    correct_answer_required: bool = False
    correct_answer: str = ""
    numerical_response_required: bool = False
    response_data_identifier: str = ""
    response_required: bool = False


class ChoiceConfig(InternalModel):
    set_alert: bool = False
    option_score: bool = False
    randomize_response_options: bool = False


class ResponseType(str, Enum):
    TEXT = "text"
    CHOICE = "choice"


class CheckboxItemConfig(InternalModel):
    name: str = ""
    value: int = 0
    isVisible: bool = False
    image: str
    description: str = ""
    color: Color
    score: int

    @validator("image")
    def validate_image(cls, value):
        return validate_image(value)

    @validator("color")
    def validate_color(cls, value):
        return validate_color(value)


class CheckboxConfig(InternalModel):
    multiple_choice: bool = False
    scoring: bool = False
    min_value: int = 0
    max_value: int = 0
    color_palette: bool = False
    randomize_options: bool = False
    is_token_type: bool = False
    items: list[CheckboxItemConfig] = []


ResponseTypeConfig = TextConfig | ChoiceConfig | CheckboxConfig
