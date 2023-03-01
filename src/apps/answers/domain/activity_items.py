import uuid

from pydantic import Field

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "AnswerCreate",
    "AnswerRequest",
    "AnswerActivityItem",
    "AnswerActivityItemCreate",
    "AnswerActivityItemsCreate",
    "AnswerActivityItemsCreateRequest",
    "PublicAnswerActivityItem",
    "ActivityIdentifierBase",
    "AnswerActivityItemCreateBase",
]


class AnswerActivityItemCreateBase(InternalModel):
    """This model used for internal needs"""

    applet_id: uuid.UUID = Field(
        description="This field represents the specific applet id"
    )
    applet_history_id_version: str = Field(
        description="This field represents the applet histories id version "
        "at a particular moment in history"
    )
    activity_id: uuid.UUID = Field(
        description="This field represents the activity id"
    )
    respondent_id: uuid.UUID = Field(
        description="This field represents the user id, "
        "where the user has the respondent role"
    )


class AnswerRequest(PublicModel):
    """This model represents the answer for specific activity items"""

    activity_item_history_id: uuid.UUID = Field(
        description="This field represents the activity item's "
        "histories id at a particular moment in history"
    )
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )


class AnswerCreate(PublicModel):
    """This model represents the answer for specific activity items"""

    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's "
        "histories id version at a particular moment in history"
    )
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )


class AnswerActivityItemsCreateRequest(PublicModel):
    """This model represents the answer for activity items"""

    applet_id: uuid.UUID = Field(
        description="This field represents the specific applet id"
    )
    applet_history_version: str = Field(
        description="This field represents the applet histories version "
        "at a particular moment in history"
    )
    activity_id: uuid.UUID = Field(
        description="This field represents the activity id"
    )

    answers: list[AnswerRequest] = Field(
        description="This field represents the list of answers "
        "to a specific activity"
    )


class AnswerActivityItemCreate(AnswerActivityItemCreateBase):
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


class AnswerActivityItemsCreate(AnswerActivityItemCreateBase):
    """This model using as multiple model"""

    answers: list[AnswerCreate] = Field(
        description="This field represents the list of answers "
        "to a specific activity"
    )


class AnswerActivityItem(AnswerActivityItemCreate):
    id: uuid.UUID


class ActivityIdentifierBase(PublicModel):
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


class PublicAnswerActivityItem(ActivityIdentifierBase):
    """This model represents the public answer for activity item"""

    id: uuid.UUID
    answer: dict[str, str] = Field(
        description="This field represents the answer "
        "to a specific activity item"
    )
    activity_item_history_id_version: str = Field(
        description="This field represents the activity item's "
        "histories id version at a particular moment in history"
    )
