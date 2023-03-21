import uuid

from apps.answers.domain.activity_items import *  # noqa: F401, F403
from apps.shared.domain import InternalModel


class TextAnswer(InternalModel):
    value: str


class ChoiceAnswer(InternalModel):
    value: str


AnswerTypes = TextAnswer | ChoiceAnswer


class ActivityItemAnswerCreate(InternalModel):
    activity_item_id: uuid.UUID
    answer: AnswerTypes


class AppletAnswerCreate(InternalModel):
    applet_id: uuid.UUID
    version: str
    flow_id: uuid.UUID | None
    activity_id: uuid.UUID
    answers: list[ActivityItemAnswerCreate]
