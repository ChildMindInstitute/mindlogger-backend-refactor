import uuid

from pydantic import Field

from apps.shared.domain import InternalModel


class ActivityItemFull(InternalModel):
    id: uuid.UUID
    header_image: str | None
    question: dict[str, str]
    activity_id: uuid.UUID
    response_type: str
    answers: list
    config: dict = dict()
    ordering: int
    skippable_item: bool = False
    remove_availability_to_go_back: bool = False


class ActivityFull(InternalModel):
    id: uuid.UUID
    key: uuid.UUID
    name: str
    description: dict[str, str] = Field(default_factory=dict)
    splash_screen: str = ""
    image: str = ""
    show_all_at_once: bool = False
    is_skippable: bool = False
    is_reviewable: bool = False
    response_is_editable: bool = False
    items: list[ActivityItemFull] = Field(default_factory=list)
    is_hidden: bool = False
    ordering: int
