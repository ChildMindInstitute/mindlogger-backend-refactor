from pydantic import Field
from pydantic.types import PositiveInt

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "AnswerActivityItem",
    "AnswerActivityItemsCreate",
    "AnswerActivityItemsCreateRequest",
    "PublicAnswerActivityItem",
]


class AnswerActivityItemsCreateRequest(InternalModel):
    """This model represents the answer for activity items"""

    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )
    applet_id: int = Field(
        description="This field represents the specific applet id"
    )


class AnswerActivityItemsCreate(AnswerActivityItemsCreateRequest):
    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's id version "
        "at a particular moment in history"
    )
    respondent_id: int = Field(
        description="This field represents the user id, "
        "where the user has the respondent role"
    )


class AnswerActivityItem(AnswerActivityItemsCreate):
    id: PositiveInt


class PublicAnswerActivityItem(PublicModel):
    """This model represents the answer for activity items"""

    id: PositiveInt
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )
    applet_id: int = Field(
        description="This field represents the specific applet id"
    )
    respondent_id: int = Field(
        description="This field represents the user id, "
        "where the user has the respondent role"
    )
    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's id version "
        "at a particular moment in history"
    )
