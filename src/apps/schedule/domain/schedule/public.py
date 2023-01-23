from apps.schedule.domain.schedule import BaseEvent, BasePeriodicity
from apps.shared.domain import PublicModel

__all__ = ["PublicPeriodicity", "PublicEvent"]


class PublicPeriodicity(BasePeriodicity, PublicModel):
    pass


class PublicEvent(BaseEvent, PublicModel):
    periodicity: PublicPeriodicity
