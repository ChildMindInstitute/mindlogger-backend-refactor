from apps.schedule.domain.schedule import BaseEvent, BasePeriodicity
from apps.shared.domain import PublicModel

__all__ = ["PublicPeriodicity", "PublicEvent"]


class PublicPeriodicity(BasePeriodicity, PublicModel):
    pass


class PublicEvent(BaseEvent, PublicModel):
    periodicity: PublicPeriodicity
    user_ids: list[int] | None
    activity_id: int | None
    flow_id: int | None
