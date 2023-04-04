import uuid

from apps.activities.domain.response_type_config import ResponseType
from apps.shared.domain import InternalModel


class Text(InternalModel):
    value: str
    should_identify_response: bool = False


class SingleSelection(InternalModel):
    value: uuid.UUID
    additional_text: str | None


class MultipleSelection(InternalModel):
    value: list[uuid.UUID]
    additional_text: str | None


class Slider(InternalModel):
    value: float
    additional_text: str | None


AnswerTypes = SingleSelection | Slider | MultipleSelection | Text

ANSWER_TYPE_MAP = {
    ResponseType.TEXT: Text,
    ResponseType.SINGLESELECT: SingleSelection,
    ResponseType.MULTISELECT: MultipleSelection,
    ResponseType.SLIDER: Slider,
}


class ActivityItemAnswerCreate(InternalModel):
    activity_item_id: uuid.UUID
    answer: AnswerTypes


class AppletAnswerCreate(InternalModel):
    applet_id: uuid.UUID
    version: str
    flow_id: uuid.UUID | None = None
    activity_id: uuid.UUID
    answers: list[ActivityItemAnswerCreate]
    created_at: int | None
