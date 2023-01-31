from pydantic import Field
from pydantic.types import PositiveInt

from apps.shared.domain import PublicModel

__all__ = [
    "Answer",
    "AnswerActivityItem",
    "AnswerActivityItemsBase",
    "AnswerActivityItemCreate",
    "AnswerActivityItemsCreate",
    "AnswerActivityItemsCreateRequest",
    "PublicAnswerActivityItem",
    "RespondentActivityIdentifier",
]


class Answer(PublicModel):
    """This model represents the answer for specific activity items"""

    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's "
        "histories id version at a particular moment in history"
    )
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )


class AnswerActivityItemsBase(PublicModel):
    """This model used for internal needs"""

    applet_id: int = Field(
        description="This field represents the specific applet id"
    )
    applet_history_id_version: str = Field(
        description="This field represents the applet histories id version "
        "at a particular moment in history"
    )
    activity_id: int = Field(
        description="This field represents the activity id"
    )


class RespondentActivityIdentifier(PublicModel):
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
    activity_id: int = Field(
        description="This field represents the activity id"
    )


class AnswerActivityItemsCreateRequest(AnswerActivityItemsBase):
    """This model represents the answer for activity items"""

    answers: list[Answer] = Field(
        description="This field represents the list of answers "
        "to a specific activity"
    )


class AnswerActivityItemsCreate(AnswerActivityItemsBase):
    """This model using as multiple model"""

    respondent_id: int = Field(
        description="This field represents the user id, "
        "where the user has the respondent role"
    )
    answers: list[Answer] = Field(
        description="This field represents the list of answers "
        "to a specific activity"
    )


class AnswerActivityItemCreate(AnswerActivityItemsBase):
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


class AnswerActivityItem(AnswerActivityItemCreate):
    id: PositiveInt


class PublicAnswerActivityItem(PublicModel):
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
    activity_id: int = Field(
        description="This field represents the activity id"
    )
    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's "
        "histories id version at a particular moment in history"
    )
