import uuid

from apps.answers.domain.answer_types import AnswerTypes
from apps.shared.domain import InternalModel

__all__ = [
    "ActivityAnswerCreate",
    "ActivityItemAnswerCreate",
]


class ActivityItemAnswerCreate(InternalModel):
    activity_item_id: uuid.UUID
    answer: AnswerTypes


class ActivityAnswerCreate(InternalModel):
    applet_id: uuid.UUID
    version: str
    activity_id: uuid.UUID
    answers: list[ActivityItemAnswerCreate]
