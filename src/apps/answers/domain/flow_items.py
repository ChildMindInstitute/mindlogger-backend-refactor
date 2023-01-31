from pydantic import Field
from pydantic.types import PositiveInt

from apps.shared.domain import PublicModel

__all__ = [
    "AnswerFlow",
    "AnswerFlowItem",
    "AnswerFlowItemsBase",
    "AnswerFlowItemCreate",
    "AnswerFlowItemsCreate",
    "AnswerFlowItemsCreateRequest",
    "PublicAnswerFlowItem",
    "RespondentFlowIdentifier",
]


class AnswerFlow(PublicModel):
    """This model represents the answer for specific activity items for flow"""

    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's "
        "histories id version at a particular moment in history"
    )
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )


class AnswerFlowItemsBase(PublicModel):
    """This model used for internal needs"""

    applet_id: int = Field(
        description="This field represents the specific applet id"
    )
    applet_history_id_version: str = Field(
        description="This field represents the applet histories id version "
        "at a particular moment in history"
    )
    flow_item_history_id_version: str = Field(
        description="This field represents the flow item history id version"
    )


class RespondentFlowIdentifier(PublicModel):
    """This model used for internal needs"""

    respondent_id: int = Field(
        description="This field represents the user id, "
        "where the user has the respondent role"
    )
    applet_id: int = Field(
        description="This field represents the specific applet id"
    )
    applet_history_id_version: str = Field(
        description="This field represents the applet histories id version "
        "at a particular moment in history"
    )
    flow_item_history_id_version: str = Field(
        description="This field represents the flow item history id version"
    )


class AnswerFlowItemsCreateRequest(AnswerFlowItemsBase):
    """This model represents the answer for activity items"""

    answers: list[AnswerFlow] = Field(
        description="This field represents the list of answers "
        "to a specific activity"
    )


class AnswerFlowItemsCreate(AnswerFlowItemsBase):
    """This model using as multiple model"""

    respondent_id: int = Field(
        description="This field represents the user id, "
        "where the user has the respondent role"
    )
    answers: list[AnswerFlow] = Field(
        description="This field represents the list of answers "
        "to a specific activity"
    )


class AnswerFlowItemCreate(AnswerFlowItemsBase):
    """This model represents the answer for
    activity items for save in database
    """

    respondent_id: int = Field(
        description="This field represents the user id, "
        "where the user has the respondent role"
    )

    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's "
        "histories id version at a particular moment in history"
    )
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )


class AnswerFlowItem(AnswerFlowItemCreate):
    id: PositiveInt


class PublicAnswerFlowItem(PublicModel):
    """This model represents the public answer for activity item"""

    id: PositiveInt
    respondent_id: int = Field(
        description="This field represents the user id, "
        "where the user has the respondent role"
    )
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )
    applet_id: int = Field(
        description="This field represents the specific applet id"
    )
    applet_history_id_version: str = Field(
        description="This field represents the applet histories id version "
        "at a particular moment in history"
    )
    flow_item_history_id_version: str = Field(
        description="This field represents the flow item history id version"
    )
    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's "
        "histories id version at a particular moment in history"
    )
