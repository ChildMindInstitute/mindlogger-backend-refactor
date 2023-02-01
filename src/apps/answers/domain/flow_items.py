from pydantic import Field
from pydantic.types import PositiveInt

from apps.shared.domain import PublicModel, InternalModel

__all__ = [
    "AnswerFlowRequest",
    "AnswerFlowCreate",
    "AnswerFlowItem",
    "AnswerFlowItemCreate",
    "AnswerFlowItemsCreate",
    "AnswerFlowItemsCreateRequest",
    "PublicAnswerFlowItem",
    "FlowIdentifierBase",
    "AnswerFlowItemCreateBase",
]


class AnswerFlowItemCreateBase(InternalModel):
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
    respondent_id: int = Field(
        description="This field represents the user id, "
        "where the user has the respondent role"
    )


class AnswerFlowRequest(PublicModel):
    """This model represents the answer for specific activity items"""

    activity_item_history_id: int = Field(
        description="This field represents the activity item's "
        "histories id at a particular moment in history"
    )
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )


class AnswerFlowCreate(PublicModel):
    """This model represents the answer for specific activity items"""

    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's "
        "histories id version at a particular moment in history"
    )
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )


class AnswerFlowItemsCreateRequest(PublicModel):
    """This model represents the answer for activity items"""

    applet_id: int = Field(
        description="This field represents the specific applet id"
    )
    applet_history_version: str = Field(
        description="This field represents the applet histories version "
        "at a particular moment in history"
    )
    flow_item_history_id: int = Field(
        description="This field represents the flow item history id"
    )

    answers: list[AnswerFlowRequest] = Field(
        description="This field represents the list of answers "
        "to a specific activity"
    )


class AnswerFlowItemCreate(AnswerFlowItemCreateBase):
    """This model represents the answer for
    activity items for save in database
    """

    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's "
        "histories id version at a particular moment in history"
    )
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )


class AnswerFlowItemsCreate(AnswerFlowItemCreateBase):
    """This model using as multiple model"""

    answers: list[AnswerFlowCreate] = Field(
        description="This field represents the list of answers "
        "to a specific activity"
    )


class AnswerFlowItem(AnswerFlowItemCreate):
    id: PositiveInt


class FlowIdentifierBase(PublicModel):
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


class PublicAnswerFlowItem(FlowIdentifierBase):
    """This model represents the public answer for activity item"""

    id: PositiveInt
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )
    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's "
        "histories id version at a particular moment in history"
    )
