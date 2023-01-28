from pydantic import Field
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "AnswerFlowItem",
    "AnswerFlowItemsCreate",
    "AnswerFlowItemsCreateRequest",
    "PublicAnswerFlowItem",
]


class AnswerFlowItemsCreateRequest(InternalModel):
    """This model represents the answer for flow items"""

    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific flow item"
    )
    applet_id: int = Field(
        description="This field represents the specific applet id"
    )


class AnswerFlowItemsCreate(AnswerFlowItemsCreateRequest):
    flow_item_history_id_version: str = Field(
        description="This field represents the flow item's id version "
        "at a particular moment in history"
    )
    respondent_id: int = Field(
        description="This field represents the user id, "
        "where the user has the respondent role"
    )


class AnswerFlowItem(AnswerFlowItemsCreate):
    id: PositiveInt


class PublicAnswerFlowItem(PublicModel):
    """This model represents the answer for flow items"""

    id: PositiveInt
    answer: dict[str, str] = Field(
        description="This field represents the answer to a specific flow item"
    )
    applet_id: int = Field(
        description="This field represents the specific applet id"
    )
    respondent_id: int = Field(
        description="This field represents the user id, "
        "where the user has the respondent role"
    )
    flow_item_history_id_version: str = Field(
        description="This field represents the flow item's id version "
        "at a particular moment in history"
    )
