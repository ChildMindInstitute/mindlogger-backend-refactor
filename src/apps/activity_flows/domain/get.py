import pydantic.types as types

from apps.shared.domain import InternalModel

__all__ = ["ActivityFlow", "ActivityFlowItem"]


class ActivityFlowItem(InternalModel):
    id: int
    activity_flow_id: int
    activity_id: int
    ordering: int


class ActivityFlow(InternalModel):
    id: int
    guid: types.UUID4
    name: str
    description: types.Dict[str, str]
    is_single_report: bool = False
    hide_badge: bool = False
    items: types.List[ActivityFlowItem] = []
