from apps.schedule.db.schemas import (
    ActivityEventsSchema,
    EventSchema,
    FlowEventsSchema,
    UserEventsSchema,
)
from apps.schedule.domain.schedule.internal import (
    EventCreate,
    Event,
    Periodicity,
    UserEvent,
    ActivityEvent,
    FlowEvent,
    UserEventCreate,
    ActivityEventCreate,
    FlowEventCreate,
)
from infrastructure.database import BaseCRUD

from sqlalchemy.exc import IntegrityError
from apps.schedule.errors import (
    UserEventAlreadyExists,
    ActivityEventAlreadyExists,
    FlowEventAlreadyExists,
)

__all__ = [
    "EventCRUD",
    "UserEventsCRUD",
    "ActivityEventsCRUD",
    "FlowEventsCRUD",
]


class EventCRUD(BaseCRUD[EventSchema]):
    schema_class = EventSchema

    async def save(self, schema: EventCreate) -> Event:
        """Return event instance and the created information."""
        instance: EventSchema = await self._create(
            EventSchema(**schema.dict())
        )
        event: Event = Event.from_orm(instance)
        return event

    async def get_by_id(self, id: int) -> EventSchema:
        pass

    async def get_by_user_id(self, user_id: int) -> EventSchema:
        pass

    async def get_by_activity_id(self, activity_id: int) -> EventSchema:
        pass

    async def get_by_flow_id(self, flow_id: int) -> EventSchema:
        pass

    async def update(self, schema: EventSchema) -> EventSchema:
        pass

    async def delete(self, id: int) -> EventSchema:
        pass


class UserEventsCRUD(BaseCRUD[UserEventsSchema]):
    async def save(self, schema: UserEventCreate) -> UserEventsSchema:
        """Return user event instance and the created information."""
        try:

            instance: UserEventsSchema = await self._create(
                UserEventsSchema(**schema.dict())
            )
        except IntegrityError:
            raise UserEventAlreadyExists(
                user_id=schema.user_id, event_id=schema.event_id
            )

        user_event: UserEvent = UserEvent.from_orm(instance)
        return user_event

    async def retrieve(self, id: int) -> UserEventsSchema:
        pass

    async def update(self, schema: UserEventsSchema) -> UserEventsSchema:
        pass

    async def delete(self, id: int) -> UserEventsSchema:
        pass


class ActivityEventsCRUD(BaseCRUD[ActivityEventsSchema]):
    async def save(self, schema: ActivityEventCreate) -> ActivityEvent:
        """Return activity event instance and the created information."""

        try:
            instance: ActivityEventsSchema = await self._create(
                ActivityEventsSchema(**schema.dict())
            )
        except IntegrityError:
            raise ActivityEventAlreadyExists(
                activity_id=schema.activity_id, event_id=schema.event_id
            )

        activity_event: ActivityEvent = ActivityEvent.from_orm(instance)
        return activity_event

    async def retrieve(self, id: int) -> ActivityEventsSchema:
        pass

    async def update(
        self, schema: ActivityEventsSchema
    ) -> ActivityEventsSchema:
        pass

    async def delete(self, id: int) -> ActivityEventsSchema:
        pass


class FlowEventsCRUD(BaseCRUD[FlowEventsSchema]):
    async def save(self, schema: FlowEventCreate) -> FlowEvent:
        """Return flow event instance and the created information."""
        try:
            instance: FlowEventsSchema = await self._create(
                FlowEventsSchema(**schema.dict())
            )
        except IntegrityError:
            raise FlowEventAlreadyExists(
                flow_id=schema.flow_id, event_id=schema.event_id
            )

        flow_event: FlowEvent = FlowEvent.from_orm(instance)
        return flow_event

    async def retrieve(self, id: int) -> FlowEventsSchema:
        pass

    async def update(self, schema: FlowEventsSchema) -> FlowEventsSchema:
        pass

    async def delete(self, id: int) -> FlowEventsSchema:
        pass
