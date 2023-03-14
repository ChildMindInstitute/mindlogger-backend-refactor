from apps.shared.domain import InternalModel


class TextAnswer(InternalModel):
    value: str


class ChoiceAnswer(InternalModel):
    value: str


AnswerTypes = TextAnswer | ChoiceAnswer
