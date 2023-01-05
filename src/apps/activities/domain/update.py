import pydantic.types as types
from pydantic import BaseModel

__all__ = ["ActivityUpdate", "ActivityItemUpdate"]


class ActivityItemUpdate(BaseModel):
    id: int | None
    question: types.Dict[str, str]
    response_type: str
    answers: types.List[types.Any]
    color_palette: str = ""
    timer: int = 0
    has_token_value: bool = False
    is_skippable: bool = False
    has_alert: bool = False
    has_score: bool = False
    is_random: bool = False
    is_able_to_move_to_previous: bool = False
    has_text_response: bool = False


class ActivityUpdate(BaseModel):
    id: int | None
    guid: types.UUID4
    name: str
    description: types.Dict[str, str]
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    items: types.List[ActivityItemUpdate]
