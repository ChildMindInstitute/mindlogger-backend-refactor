import datetime
import uuid

from apps.schedule.db.schemas import (
    PeriodicitySchema,
    EventSchema,
    ActivityEventsSchema,
    FlowEventsSchema,
)
from apps.schedule.crud.periodicity import PeriodicityCRUD
from apps.schedule.crud.events import (
    EventCRUD,
    ActivityEventsCRUD,
    FlowEventsCRUD,
)
from apps.migrate.services.event_service import (
    DEFAULT_PERIODICITY_TYPE,
    TIMER_TYPE,
    NOT_SET,
)
from infrastructure.database import atomic


__all__ = [
    "DefaultEventAddingService",
]


class DefaultEventAddingService:
    def __init__(
        self,
        session,
        activities: list[tuple[str, str]],
        flows: list[tuple[str, str]],
    ):
        self.session = session
        self.activities = activities
        self.flows = flows

    async def run_adding_default_event(self):
        await self._add_for_activities()
        await self._add_for_flows()

    async def _add_for_activities(self):
        for activity_id, applet_id in self.activities:
            event = await self._create_default_event(applet_id)

            activity_event_data: dict = {
                "activity_id": uuid.UUID(activity_id),
                "event_id": event.id,
                "migrated_date": datetime.datetime.utcnow(),
                "migrated_updated": datetime.datetime.utcnow(),
            }
            activity = ActivityEventsSchema(**activity_event_data)

            async with atomic(self.session):
                await ActivityEventsCRUD(self.session)._create(activity)

    async def _add_for_flows(self):
        for flow_id, applet_id in self.flows:
            event = await self._create_default_event(applet_id)

            flow_event_data: dict = {
                "flow_id": uuid.UUID(flow_id),
                "event_id": event.id,
                "migrated_date": datetime.datetime.utcnow(),
                "migrated_updated": datetime.datetime.utcnow(),
            }
            flow = FlowEventsSchema(**flow_event_data)

            async with atomic(self.session):
                await FlowEventsCRUD(self.session)._create(flow)

    async def _create_default_event(self, applet_id: str) -> EventSchema:
        periodicity_data: dict = {}
        periodicity_data["type"] = DEFAULT_PERIODICITY_TYPE
        periodicity = PeriodicitySchema(**periodicity_data)

        async with atomic(self.session):
            await PeriodicityCRUD(self.session)._create(periodicity)

        event_data: dict = {}
        event_data["applet_id"] = uuid.UUID(applet_id)
        event_data["periodicity_id"] = periodicity.id
        event_data["timer_type"] = TIMER_TYPE[NOT_SET]
        event_data["migrated_date"] = datetime.datetime.utcnow()
        event_data["migrated_updated"] = datetime.datetime.utcnow()
        event = EventSchema(**event_data)

        async with atomic(self.session):
            await EventCRUD(self.session)._create(event)

        return event
