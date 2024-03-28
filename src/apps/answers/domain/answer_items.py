import uuid

from apps.shared.domain.base import InternalModel


class AnswerItem(InternalModel):
    answer_id: uuid.UUID
    respondent_id: uuid.UUID
    is_assessment: bool
    assessment_activity_id: str | None
