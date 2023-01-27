from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "AnswerFlowItem",
    "AnswerFlowItemsCreate",
    "AnswerFlowItemsCreateRequest",
    "PublicAnswerFlowItem",
]


class AnswerFlowItemsCreateRequest(InternalModel):
    """This model represents answer flow items
    `create request` data model.
    """

    answer: dict[str, str]
    applet_id: int


class AnswerFlowItemsCreate(AnswerFlowItemsCreateRequest):
    flow_item_history_id_version: str
    respondent_id: int


class AnswerFlowItem(AnswerFlowItemsCreate):
    id: PositiveInt


class PublicAnswerFlowItem(PublicModel):
    """This model represents answer flow items
    `response` data model.
    """

    id: PositiveInt
    answer: dict[str, str]
    applet_id: int
    respondent_id: int
    flow_item_history_id_version: str
