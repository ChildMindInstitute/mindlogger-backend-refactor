from apps.shared.domain import PublicModel

__all__ = [
    "AnswerCreate",
    "AnswerCreateRequest",
]


class AnswerCreateRequest(PublicModel):
    applet_history_id_version: str
    activity_history_id_version: str
    activity_item_history_id_version: str
    flow_history_id_version: str
    flow_item_history_id_version: str
    answer: str


class AnswerCreate(AnswerCreateRequest):
    user_id: int
