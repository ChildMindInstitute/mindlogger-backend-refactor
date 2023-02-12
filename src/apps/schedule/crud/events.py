from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query
from sqlalchemy.sql import and_, distinct, func, select, update

from apps.activities.db.schemas import ActivitySchema
from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.schedule.db.schemas import (
    ActivityEventsSchema,
    EventSchema,
    FlowEventsSchema,
    PeriodicitySchema,
    UserEventsSchema,
)
from apps.schedule.domain.constants import PeriodicityType
from apps.schedule.domain.schedule.internal import (
    ActivityEvent,
    ActivityEventCreate,
    Event,
    EventCreate,
    EventUpdate,
    FlowEvent,
    FlowEventCreate,
    UserEvent,
    UserEventCreate,
)
from apps.schedule.domain.schedule.public import (
    ActivityEventCount,
    FlowEventCount,
)
from apps.schedule.errors import (
    ActivityEventAlreadyExists,
    EventError,
    EventNotFoundError,
    FlowEventAlreadyExists,
    UserEventAlreadyExists,
)
from infrastructure.database import BaseCRUD

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

        try:
            instance: EventSchema = await self._create(
                EventSchema(**schema.dict())
            )
        # Raise exception if applet doesn't exist
        except IntegrityError as e:
            raise EventError(message=str(e))

        event: Event = Event.from_orm(instance)
        return event

    async def get_by_id(self, pk: int) -> Event:
        """Return event instance."""
        query: Query = select(EventSchema)
        query = query.where(EventSchema.id == pk)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712

        result = await self._execute(query)
        instance = result.scalars().first()

        if not instance:
            raise EventNotFoundError(key="id", value=str(id))

        event: Event = Event.from_orm(instance)
        return event

    async def get_all_by_applet_id(self, applet_id: int) -> EventSchema:
        """Return event instance."""
        query: Query = select(EventSchema)
        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712

        result = await self._execute(query)
        return result.scalars().all()

    async def delete_by_applet_id(self, applet_id: int) -> None:
        """Delete all events by applet id."""
        query: Query = update(EventSchema)
        query = query.where(EventSchema.applet_id == applet_id)
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def delete_by_id(self, pk: int) -> None:
        """Delete event by event id."""
        query: Query = update(EventSchema)
        query = query.where(EventSchema.id == pk)
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def update(self, pk: int, schema: EventUpdate) -> Event:
        """Update event by event id."""
        instance = await self._update_one(
            lookup="id",
            value=pk,
            schema=EventSchema(**schema.dict()),
        )
        event: Event = Event.from_orm(instance)
        return event

    async def get_all_by_applet_and_user(
        self, applet_id: int, user_id: int
    ) -> list[EventSchema]:
        """Get events by applet_id and user_id"""
        query: Query = select(EventSchema)
        query = query.join(
            UserEventsSchema,
            and_(
                EventSchema.id == UserEventsSchema.event_id,
                UserEventsSchema.user_id == user_id,
            ),
        )

        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712

        result = await self._execute(query)
        return result.scalars().all()

    async def delete_by_ids(self, ids: list[int]) -> None:
        """Delete event by event ids."""
        query: Query = update(EventSchema)
        query = query.where(EventSchema.id.in_(ids))
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def get_all_by_applet_and_activity(
        self, applet_id: int, activity_id: int
    ) -> list[EventSchema]:
        """Get events by applet_id and activity_id"""
        query: Query = select(EventSchema)
        query = query.join(
            ActivityEventsSchema,
            and_(
                EventSchema.id == ActivityEventsSchema.event_id,
                ActivityEventsSchema.activity_id == activity_id,
            ),
        )

        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712

        result = await self._execute(query)
        return result.scalars().all()

    async def get_all_by_applet_and_flow(
        self, applet_id: int, flow_id: int
    ) -> list[EventSchema]:
        """Get events by applet_id and flow_id"""
        query: Query = select(EventSchema)
        query = query.join(
            FlowEventsSchema,
            and_(
                EventSchema.id == FlowEventsSchema.event_id,
                FlowEventsSchema.flow_id == flow_id,
            ),
        )

        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712

        result = await self._execute(query)
        return result.scalars().all()


class UserEventsCRUD(BaseCRUD[UserEventsSchema]):
    schema_class = UserEventsSchema

    async def save(self, schema: UserEventCreate) -> UserEvent:
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

    async def get_by_event_id(self, event_id: int) -> int:
        """Return user event instances."""
        query: Query = select(distinct(UserEventsSchema.user_id))
        query = query.where(UserEventsSchema.event_id == event_id)
        query = query.where(UserEventsSchema.is_deleted == False)  # noqa: E712
        result = await self._execute(query)
        results: int = result.scalars().one_or_none()
        return results

    async def delete_all_by_event_ids(self, event_ids: list[int]):
        """Delete all user events by event ids."""
        query: Query = update(UserEventsSchema)
        query = query.where(UserEventsSchema.event_id.in_(event_ids))
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def delete_all_by_events_and_user(
        self, event_ids: list[int], user_id: int
    ):
        """Delete all user events by event ids."""
        query: Query = update(UserEventsSchema)
        query = query.where(UserEventsSchema.event_id.in_(event_ids))
        query = query.where(UserEventsSchema.user_id == user_id)
        query = query.values(is_deleted=True)
        await self._execute(query)


class ActivityEventsCRUD(BaseCRUD[ActivityEventsSchema]):
    schema_class = ActivityEventsSchema

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

    async def get_by_event_id(self, event_id: int) -> int:
        """Return activity event instances."""
        query: Query = select(ActivityEventsSchema.activity_id)
        query = query.where(ActivityEventsSchema.event_id == event_id)
        result = await self._execute(query)
        activity_id: int = result.scalars().one_or_none()
        return activity_id

    async def delete_all_by_event_ids(self, event_ids: list[int]):
        """Delete all activity events by event ids."""
        query: Query = update(ActivityEventsSchema)
        query = query.where(ActivityEventsSchema.event_id.in_(event_ids))
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def count_by_applet(
        self, applet_id: int
    ) -> list[ActivityEventCount]:
        """Return activity ids with event count."""

        query: Query = select(
            ActivitySchema.id,
            func.count(*[ActivityEventsSchema.event_id]).label("count"),
            ActivitySchema.name,
        )
        query = query.select_from(ActivitySchema)
        query = query.join(
            ActivityEventsSchema,
            and_(
                ActivitySchema.id == ActivityEventsSchema.activity_id,
                ActivityEventsSchema.is_deleted == False,  # noqa: E712
            ),
            isouter=True,
        )
        query = query.join(
            EventSchema, ActivityEventsSchema.event_id == EventSchema.id
        )
        query = query.join(
            PeriodicitySchema,
            EventSchema.periodicity_id == PeriodicitySchema.id,
        )

        query = query.filter(ActivitySchema.is_deleted == False)  # noqa: E712
        query = query.filter(ActivitySchema.applet_id == applet_id)
        query = query.filter(PeriodicitySchema.type != PeriodicityType.always)
        query = query.group_by(ActivitySchema.applet_id, ActivitySchema.id)
        result = await self._execute(query)

        activity_event_counts: list[ActivityEventCount] = [
            ActivityEventCount(
                activity_id=activity_id,
                count=count,
                activity_name=name,
            )
            for activity_id, count, name in result
        ]

        return activity_event_counts

    async def count_by_activity(self, activity_id: int) -> int:
        """Return event count."""

        query: Query = select(
            func.count(*[ActivityEventsSchema.event_id]).label("count"),
        )
        query = query.filter(ActivityEventsSchema.activity_id == activity_id)
        query = query.filter(
            ActivityEventsSchema.is_deleted == False  # noqa: E712
        )
        result = await self._execute(query)

        count: int = result.scalar()
        return count

    async def get_by_event_ids(self, event_ids: list[int]) -> list[int]:
        """Return activity event instances."""
        query: Query = select(distinct(ActivityEventsSchema.activity_id))
        query = query.where(ActivityEventsSchema.event_id.in_(event_ids))
        result = await self._execute(query)
        activity_ids: list[int] = result.scalars().all()
        return activity_ids


class FlowEventsCRUD(BaseCRUD[FlowEventsSchema]):
    schema_class = FlowEventsSchema

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

    async def get_by_event_id(self, event_id: int) -> int:
        """Return flow event instances."""
        query: Query = select(FlowEventsSchema.flow_id)
        query = query.where(FlowEventsSchema.event_id == event_id)
        result = await self._execute(query)
        flow_id: int = result.scalars().one_or_none()
        return flow_id

    async def delete_all_by_event_ids(self, event_ids: list[int]):
        """Delete all flow events by event ids."""
        query: Query = update(FlowEventsSchema)
        query = query.where(FlowEventsSchema.event_id.in_(event_ids))
        query = query.values(is_deleted=True)
        await self._execute(query)

    async def count_by_applet(self, applet_id: int) -> list[FlowEventCount]:
        """Return flow ids with event count."""

        query: Query = select(
            ActivityFlowSchema.id,
            func.count(*[FlowEventsSchema.id]).label("count"),
            ActivityFlowSchema.name,
        )
        query = query.select_from(ActivityFlowSchema)

        query = query.join(
            FlowEventsSchema,
            and_(
                FlowEventsSchema.flow_id == ActivityFlowSchema.id,
                FlowEventsSchema.is_deleted == False,  # noqa: E712
            ),
            isouter=True,
        )
        query = query.join(
            EventSchema, FlowEventsSchema.event_id == EventSchema.id
        )
        query = query.join(
            PeriodicitySchema,
            EventSchema.periodicity_id == PeriodicitySchema.id,
        )

        query = query.filter(ActivityFlowSchema.applet_id == applet_id)
        query = query.filter(
            ActivityFlowSchema.is_deleted == False  # noqa: E712
        )
        query = query.filter(PeriodicitySchema.type != PeriodicityType.always)
        query = query.group_by(
            ActivityFlowSchema.applet_id, ActivityFlowSchema.id
        )

        result = await self._execute(query)

        flow_event_counts: list[FlowEventCount] = [
            FlowEventCount(
                flow_id=flow_id,
                count=count,
                flow_name=name,
            )
            for flow_id, count, name in result
        ]

        return flow_event_counts

    async def get_by_event_ids(self, event_ids: list[int]) -> list[int]:
        """Return flow event instances."""
        query: Query = select(distinct(FlowEventsSchema.flow_id))
        query = query.where(FlowEventsSchema.event_id.in_(event_ids))
        result = await self._execute(query)
        flow_ids: list[int] = result.scalars().all()
        return flow_ids

    async def count_by_flow(self, flow_id: int) -> int:
        """Return event count."""

        query: Query = select(
            func.count(*[FlowEventsSchema.event_id]).label("count"),
        )
        query = query.filter(FlowEventsSchema.flow_id == flow_id)
        query = query.filter(
            FlowEventsSchema.is_deleted == False  # noqa: E712
        )
        result = await self._execute(query)

        count: int = result.scalar()
        return count
