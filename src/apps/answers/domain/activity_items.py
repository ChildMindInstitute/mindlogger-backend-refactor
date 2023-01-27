from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "AnswerActivityItem",
    "AnswerActivityItemsCreate",
    "AnswerActivityItemsCreateRequest",
    "PublicAnswerActivityItem",
]


class AnswerActivityItemsCreateRequest(InternalModel):
    """This model represents answer activity items
    `create request` data model.
    """

    answer: dict[str, str]
    applet_id: int


class AnswerActivityItemsCreate(AnswerActivityItemsCreateRequest):
    activity_item_history_id_version: str
    respondent_id: int


class AnswerActivityItem(AnswerActivityItemsCreate):
    id: PositiveInt


class PublicAnswerActivityItem(PublicModel):
    """This model represents answer activity items
    `response` data model.
    """

    id: PositiveInt
    answer: dict[str, str]
    applet_id: int
    respondent_id: int
    activity_item_history_id_version: str
