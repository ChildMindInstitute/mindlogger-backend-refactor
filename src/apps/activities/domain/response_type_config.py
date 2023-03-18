from enum import Enum

from apps.shared.domain import InternalModel


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
    name: str
    value: int
    isVisible: bool
    image: str
    description: str
    color: str
    score: int


class CheckboxConfig(InternalModel):
    multiple_choice: bool = False
    scoring: bool = False
    min_value: int = 0
    max_value: int = 0
    color_palette: bool = False
    randomize_options: bool = False
    is_token_type: bool = False
    items: list[CheckboxItemConfig] = []


ResponseTypeConfig = TextConfig | ChoiceConfig
