import uuid
from datetime import date

from infrastructure.logger import logger
from sqlalchemy.exc import IntegrityError, MultipleResultsFound
from sqlalchemy.orm import Query
from sqlalchemy.sql import and_, delete, distinct, func, or_, select

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
    EventFull,
    EventUpdate,
    EventWithActivityOrFlowId,
    FlowEvent,
    FlowEventCreate,
    Periodicity,
    UserEvent,
    UserEventCreate,
)
from apps.schedule.domain.schedule.public import ActivityEventCount, FlowEventCount
from apps.schedule.errors import (
    ActivityEventAlreadyExists,
    EventError,
    EventNotFoundError,
    FlowEventAlreadyExists,
    UserEventAlreadyExists,
)
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
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
            instance: EventSchema = await self._create(EventSchema(**schema.dict()))
        # Raise exception if applet doesn't exist
        except IntegrityError as e:
            raise EventError(message=str(e))

        event: Event = Event.from_orm(instance)
        return event

    async def get_by_id(self, pk: uuid.UUID) -> Event:
        """Return event instance."""
        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.id == pk)
        # query = query.where(EventSchema.is_deleted == False)  # noqa: E712

        result = await self._execute(query)
        instance = result.scalars().one_or_none()

        if not instance:
            raise EventNotFoundError(key="id", value=str(pk))

        event: Event = Event.from_orm(instance)
        return event

    async def get_all_by_applet_id_with_filter(
        self, applet_id: uuid.UUID, respondent_id: uuid.UUID | None = None
    ) -> list[EventSchema]:
        """Return event instance."""
        query: Query = select(EventSchema)
        query = query.join(
            UserEventsSchema,
            UserEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )
        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712
        if respondent_id:
            query = query.where(UserEventsSchema.user_id == respondent_id)
        else:
            query = query.where(UserEventsSchema.user_id == None)  # noqa: E711

        result = await self._execute(query)
        return result.scalars().all()

    async def get_public_by_applet_id(self, applet_id: uuid.UUID) -> list[EventSchema]:
        """Return event instance."""
        query: Query = select(EventSchema)
        query = query.join(
            UserEventsSchema,
            UserEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )
        query = query.where(EventSchema.applet_id == applet_id)
        query = query.distinct(EventSchema.id)
        query = query.where(UserEventsSchema.user_id == None)  # noqa: E711
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712

        result = await self._execute(query)
        return result.scalars().all()

    async def update(self, pk: uuid.UUID, schema: EventUpdate) -> Event:
        """Update event by event id."""
        instance = await self._update_one(
            lookup="id",
            value=pk,
            schema=EventSchema(**schema.dict()),
        )
        event: Event = Event.from_orm(instance)
        return event

    async def get_all_by_applet_and_user(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> list[EventFull]:
        """Get events by applet_id and user_id"""

        query: Query = select(
            EventSchema,
            PeriodicitySchema.start_date,
            PeriodicitySchema.end_date,
            PeriodicitySchema.selected_date,
            PeriodicitySchema.type,
            ActivityEventsSchema.activity_id,
            FlowEventsSchema.flow_id,
        )
        query = query.join(
            UserEventsSchema,
            and_(
                EventSchema.id == UserEventsSchema.event_id,
                UserEventsSchema.user_id == user_id,
            ),
        )

        query = query.join(
            PeriodicitySchema,
            PeriodicitySchema.id == EventSchema.periodicity_id,
        )

        query = query.join(
            FlowEventsSchema,
            FlowEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )
        query = query.join(
            ActivityEventsSchema,
            ActivityEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )

        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712

        db_result = await self._execute(query)

        events = []
        for row in db_result:
            events.append(
                EventFull(
                    id=row.EventSchema.id,
                    start_time=row.EventSchema.start_time,
                    end_time=row.EventSchema.end_time,
                    access_before_schedule=row.EventSchema.access_before_schedule,  # noqa: E501
                    one_time_completion=row.EventSchema.one_time_completion,
                    timer=row.EventSchema.timer,
                    timer_type=row.EventSchema.timer_type,
                    user_id=user_id,
                    periodicity=Periodicity(
                        id=row.EventSchema.periodicity_id,
                        type=row.type,
                        start_date=row.start_date,
                        end_date=row.end_date,
                        selected_date=row.selected_date,
                    ),
                    activity_id=row.activity_id,
                    flow_id=row.flow_id,
                )
            )
        return events

    async def get_all_by_applets_and_user(
        self,
        applet_ids: list[uuid.UUID],
        user_id: uuid.UUID,
        min_end_date: date | None = None,
        max_start_date: date | None = None,
    ) -> tuple[dict[uuid.UUID, list[EventFull]], set[uuid.UUID]]:
        """Get events by applet_ids and user_id
        Return {applet_id: [EventFull]}"""

        query: Query = select(
            EventSchema,
            PeriodicitySchema.start_date,
            PeriodicitySchema.end_date,
            PeriodicitySchema.selected_date,
            PeriodicitySchema.type,
            ActivityEventsSchema.activity_id,
            FlowEventsSchema.flow_id,
        )
        query = query.join(
            UserEventsSchema,
            and_(
                EventSchema.id == UserEventsSchema.event_id,
                UserEventsSchema.user_id == user_id,
            ),
        )

        query = query.join(
            PeriodicitySchema,
            PeriodicitySchema.id == EventSchema.periodicity_id,
        )

        query = query.join(
            FlowEventsSchema,
            FlowEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )
        query = query.join(
            ActivityEventsSchema,
            ActivityEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )

        query = query.where(EventSchema.applet_id.in_(applet_ids))
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712
        if min_end_date and max_start_date:
            query = query.where(
                or_(
                    PeriodicitySchema.type == PeriodicityType.ALWAYS,
                    and_(
                        PeriodicitySchema.type != PeriodicityType.ONCE,
                        or_(
                            PeriodicitySchema.start_date.is_(None),
                            PeriodicitySchema.start_date <= max_start_date,
                        ),
                        or_(
                            PeriodicitySchema.end_date.is_(None),
                            PeriodicitySchema.end_date >= min_end_date,
                        ),
                    ),
                    and_(
                        PeriodicitySchema.type == PeriodicityType.ONCE,
                        PeriodicitySchema.selected_date <= max_start_date,
                        PeriodicitySchema.selected_date >= min_end_date,
                    ),
                )
            )

        db_result = await self._execute(query)

        events_map: dict[uuid.UUID, list[EventFull]] = dict()
        event_ids: set[uuid.UUID] = set()
        for row in db_result:
            event_ids.add(row.EventSchema.id)
            events_map.setdefault(row.EventSchema.applet_id, list())
            events_map[row.EventSchema.applet_id].append(
                EventFull(
                    id=row.EventSchema.id,
                    start_time=row.EventSchema.start_time,
                    end_time=row.EventSchema.end_time,
                    access_before_schedule=row.EventSchema.access_before_schedule,  # noqa: E501
                    one_time_completion=row.EventSchema.one_time_completion,
                    timer=row.EventSchema.timer,
                    timer_type=row.EventSchema.timer_type,
                    user_id=user_id,
                    periodicity=Periodicity(
                        id=row.EventSchema.periodicity_id,
                        type=row.type,
                        start_date=row.start_date,
                        end_date=row.end_date,
                        selected_date=row.selected_date,
                    ),
                    activity_id=row.activity_id,
                    flow_id=row.flow_id,
                )
            )

        return events_map, event_ids

    async def delete_by_ids(self, ids: list[uuid.UUID]) -> None:
        """Delete event by event ids."""
        query: Query = delete(EventSchema)
        query = query.where(EventSchema.id.in_(ids))
        await self._execute(query)

    async def get_all_by_applet_and_activity(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID,
        respondent_id: uuid.UUID | None,
        only_always_available: bool = False,
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
        # differentiate general and individual events
        query = query.join(
            UserEventsSchema,
            EventSchema.id == UserEventsSchema.event_id,
            isouter=True,
        )
        # select only always available if requested
        if only_always_available:
            query = query.join(
                PeriodicitySchema,
                and_(
                    EventSchema.periodicity_id == PeriodicitySchema.id,
                    PeriodicitySchema.type == PeriodicityType.ALWAYS,
                ),
            )
        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712

        query = query.where(UserEventsSchema.user_id == respondent_id)

        result = await self._execute(query)
        return result.scalars().all()

    async def get_all_by_applet_and_flow(
        self,
        applet_id: uuid.UUID,
        flow_id: uuid.UUID,
        respondent_id: uuid.UUID | None,
        only_always_available: bool = False,
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

        # differentiate general and individual events
        query = query.join(
            UserEventsSchema,
            EventSchema.id == UserEventsSchema.event_id,
            isouter=True,
        )

        # select only always available if requested
        if only_always_available:
            query = query.join(
                PeriodicitySchema,
                and_(
                    EventSchema.periodicity_id == PeriodicitySchema.id,
                    PeriodicitySchema.type == PeriodicityType.ALWAYS,
                ),
            )

        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712

        query = query.where(UserEventsSchema.user_id == respondent_id)

        result = await self._execute(query)
        return result.scalars().all()

    async def get_general_events_by_user(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> list[EventFull]:
        """Get general events by applet_id and user_id"""
        # select flow_ids to exclude
        flow_ids = (
            select(distinct(FlowEventsSchema.flow_id))
            .select_from(FlowEventsSchema)
            .join(
                UserEventsSchema,
                UserEventsSchema.event_id == FlowEventsSchema.event_id,
            )
            .join(
                EventSchema,
                EventSchema.id == FlowEventsSchema.event_id,
            )
            .where(UserEventsSchema.user_id == user_id)
            .where(EventSchema.applet_id == applet_id)
        )
        activity_ids = (
            select(distinct(ActivityEventsSchema.activity_id))
            .select_from(ActivityEventsSchema)
            .join(
                UserEventsSchema,
                UserEventsSchema.event_id == ActivityEventsSchema.event_id,
            )
            .join(
                EventSchema,
                EventSchema.id == ActivityEventsSchema.event_id,
            )
            .where(UserEventsSchema.user_id == user_id)
            .where(EventSchema.applet_id == applet_id)
        )

        query: Query = select(
            EventSchema,
            PeriodicitySchema.start_date,
            PeriodicitySchema.end_date,
            PeriodicitySchema.selected_date,
            PeriodicitySchema.type,
            ActivityEventsSchema.activity_id,
            FlowEventsSchema.flow_id,
        )
        query = query.join(
            PeriodicitySchema,
            PeriodicitySchema.id == EventSchema.periodicity_id,
        )

        query = query.join(
            FlowEventsSchema,
            FlowEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )
        query = query.join(
            ActivityEventsSchema,
            ActivityEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )
        query = query.join(
            UserEventsSchema,
            UserEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )

        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712
        query = query.where(
            or_(
                FlowEventsSchema.flow_id.is_(None),
                FlowEventsSchema.flow_id.not_in(flow_ids),
            )
        )
        query = query.where(
            or_(
                ActivityEventsSchema.activity_id.is_(None),
                ActivityEventsSchema.activity_id.not_in(activity_ids),
            )
        )
        query = query.where(UserEventsSchema.user_id == None)  # noqa: E711

        db_result = await self._execute(query)

        events = []
        for row in db_result:
            events.append(
                EventFull(
                    id=row.EventSchema.id,
                    start_time=row.EventSchema.start_time,
                    end_time=row.EventSchema.end_time,
                    access_before_schedule=row.EventSchema.access_before_schedule,  # noqa: E501
                    one_time_completion=row.EventSchema.one_time_completion,
                    timer=row.EventSchema.timer,
                    timer_type=row.EventSchema.timer_type,
                    user_id=user_id,
                    periodicity=Periodicity(
                        id=row.EventSchema.periodicity_id,
                        type=row.type,
                        start_date=row.start_date,
                        end_date=row.end_date,
                        selected_date=row.selected_date,
                    ),
                    activity_id=row.activity_id,
                    flow_id=row.flow_id,
                )
            )
        return events

    async def get_general_events_by_applets_and_user(
        self,
        applet_ids: list[uuid.UUID],
        user_id: uuid.UUID,
        min_end_date: date | None = None,
        max_start_date: date | None = None,
    ) -> tuple[dict[uuid.UUID, list[EventFull]], set[uuid.UUID]]:
        """Get general events by applet_id and user_id"""
        # select flow_ids to exclude
        flow_ids = (
            select(distinct(FlowEventsSchema.flow_id))
            .select_from(FlowEventsSchema)
            .join(
                UserEventsSchema,
                UserEventsSchema.event_id == FlowEventsSchema.event_id,
            )
            .join(
                EventSchema,
                EventSchema.id == FlowEventsSchema.event_id,
            )
            .where(UserEventsSchema.user_id == user_id)
            .where(EventSchema.applet_id.in_(applet_ids))
        )
        activity_ids = (
            select(distinct(ActivityEventsSchema.activity_id))
            .select_from(ActivityEventsSchema)
            .join(
                UserEventsSchema,
                UserEventsSchema.event_id == ActivityEventsSchema.event_id,
            )
            .join(
                EventSchema,
                EventSchema.id == ActivityEventsSchema.event_id,
            )
            .where(UserEventsSchema.user_id == user_id)
            .where(EventSchema.applet_id.in_(applet_ids))
        )

        query: Query = select(
            EventSchema,
            PeriodicitySchema.start_date,
            PeriodicitySchema.end_date,
            PeriodicitySchema.selected_date,
            PeriodicitySchema.type,
            ActivityEventsSchema.activity_id,
            FlowEventsSchema.flow_id,
        )

        query = query.join(
            PeriodicitySchema,
            PeriodicitySchema.id == EventSchema.periodicity_id,
        )

        query = query.join(
            FlowEventsSchema,
            FlowEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )
        query = query.join(
            ActivityEventsSchema,
            ActivityEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )
        query = query.join(
            UserEventsSchema,
            UserEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )

        query = query.where(EventSchema.applet_id.in_(applet_ids))
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712
        query = query.where(
            or_(
                FlowEventsSchema.flow_id.is_(None),
                FlowEventsSchema.flow_id.not_in(flow_ids),
            )
        )
        query = query.where(
            or_(
                ActivityEventsSchema.activity_id.is_(None),
                ActivityEventsSchema.activity_id.not_in(activity_ids),
            )
        )
        query = query.where(UserEventsSchema.user_id == None)  # noqa: E711
        if min_end_date and max_start_date:
            query = query.where(
                or_(
                    PeriodicitySchema.type == PeriodicityType.ALWAYS,
                    and_(
                        PeriodicitySchema.type != PeriodicityType.ONCE,
                        or_(
                            PeriodicitySchema.start_date.is_(None),
                            PeriodicitySchema.start_date <= max_start_date,
                        ),
                        or_(
                            PeriodicitySchema.end_date.is_(None),
                            PeriodicitySchema.end_date >= min_end_date,
                        ),
                    ),
                    and_(
                        PeriodicitySchema.type == PeriodicityType.ONCE,
                        PeriodicitySchema.selected_date <= max_start_date,
                        PeriodicitySchema.selected_date >= min_end_date,
                    ),
                )
            )

        db_result = await self._execute(query)

        events_map: dict[uuid.UUID, list[EventFull]] = dict()
        event_ids: set[uuid.UUID] = set()
        for row in db_result:
            event_ids.add(row.EventSchema.id)
            events_map.setdefault(row.EventSchema.applet_id, list())
            events_map[row.EventSchema.applet_id].append(
                EventFull(
                    id=row.EventSchema.id,
                    start_time=row.EventSchema.start_time,
                    end_time=row.EventSchema.end_time,
                    access_before_schedule=row.EventSchema.access_before_schedule,  # noqa: E501
                    one_time_completion=row.EventSchema.one_time_completion,
                    timer=row.EventSchema.timer,
                    timer_type=row.EventSchema.timer_type,
                    user_id=user_id,
                    periodicity=Periodicity(
                        id=row.EventSchema.periodicity_id,
                        type=row.type,
                        start_date=row.start_date,
                        end_date=row.end_date,
                        selected_date=row.selected_date,
                    ),
                    activity_id=row.activity_id,
                    flow_id=row.flow_id,
                )
            )

        return events_map, event_ids

    async def count_general_events_by_user(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """Count general events by applet_id and user_id"""
        flow_ids = (
            select(distinct(FlowEventsSchema.flow_id))
            .select_from(FlowEventsSchema)
            .join(
                UserEventsSchema,
                UserEventsSchema.event_id == FlowEventsSchema.event_id,
            )
            .join(
                EventSchema,
                EventSchema.id == FlowEventsSchema.event_id,
            )
            .where(UserEventsSchema.user_id == user_id)
            .where(EventSchema.applet_id == applet_id)
        )
        activity_ids = (
            select(distinct(ActivityEventsSchema.activity_id))
            .select_from(ActivityEventsSchema)
            .join(
                UserEventsSchema,
                UserEventsSchema.event_id == ActivityEventsSchema.event_id,
            )
            .join(
                EventSchema,
                EventSchema.id == ActivityEventsSchema.event_id,
            )
            .where(UserEventsSchema.user_id == user_id)
            .where(EventSchema.applet_id == applet_id)
        )

        query: Query = select(
            func.count(EventSchema.id).label("count"),
        )

        query = query.join(
            FlowEventsSchema,
            FlowEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )
        query = query.join(
            ActivityEventsSchema,
            ActivityEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )
        query = query.join(
            UserEventsSchema,
            UserEventsSchema.event_id == EventSchema.id,
            isouter=True,
        )

        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712
        query = query.where(
            or_(
                FlowEventsSchema.flow_id.is_(None),
                FlowEventsSchema.flow_id.not_in(flow_ids),
            )
        )
        query = query.where(
            or_(
                ActivityEventsSchema.activity_id.is_(None),
                ActivityEventsSchema.activity_id.not_in(activity_ids),
            )
        )
        query = query.where(UserEventsSchema.user_id == None)  # noqa: E711
        db_result = await self._execute(query)

        return db_result.scalar()

    async def count_individual_events_by_user(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """Count individual events by applet_id and user_id"""

        query: Query = select(func.count(EventSchema.id))
        query = query.join(
            UserEventsSchema,
            and_(
                EventSchema.id == UserEventsSchema.event_id,
                UserEventsSchema.user_id == user_id,
            ),
        )

        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted == False)  # noqa: E712
        db_result = await self._execute(query)
        return db_result.scalar()

    async def get_all_by_activity_flow_ids(
        self,
        applet_id: uuid.UUID,
        activity_ids: list[uuid.UUID],
        is_activity: bool,
    ) -> list[EventWithActivityOrFlowId]:
        """Return events for given activity ids."""
        query: Query = select(self.schema_class)
        query = query.where(self.schema_class.applet_id == applet_id)

        if is_activity:
            query = query.join(
                ActivityEventsSchema,
                ActivityEventsSchema.event_id == self.schema_class.id,
            )
            query = query.where(ActivityEventsSchema.activity_id.in_(activity_ids))
        else:
            query = query.join(
                FlowEventsSchema,
                FlowEventsSchema.event_id == self.schema_class.id,
            )
            query = query.where(FlowEventsSchema.flow_id.in_(activity_ids))

        result = await self._execute(query)
        events = result.scalars().all()
        return events

    async def get_default_schedule_user_ids_by_applet_id(self, applet_id: uuid.UUID) -> list[uuid.UUID]:
        """Return user ids for default schedule."""
        individual_schedule_users = (
            select(UserEventsSchema.user_id)
            .join(EventSchema, UserEventsSchema.event_id == EventSchema.id)
            .where(EventSchema.applet_id == applet_id)
            .where(EventSchema.is_deleted == False)  # noqa: E712
        )
        query: Query = select(UserAppletAccessSchema.user_id.label("user_id"))
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == Role.RESPONDENT)
        query = query.where(UserAppletAccessSchema.is_deleted == False)  # noqa: E712
        query = query.where(UserAppletAccessSchema.user_id.not_in(individual_schedule_users))
        result = await self._execute(query)
        result = result.scalars().all()
        return result


class UserEventsCRUD(BaseCRUD[UserEventsSchema]):
    schema_class = UserEventsSchema

    async def save(self, schema: UserEventCreate) -> UserEvent:
        """Return user event instance and the created information."""
        try:
            instance: UserEventsSchema = await self._create(UserEventsSchema(**schema.dict()))
        except IntegrityError:
            raise UserEventAlreadyExists(user_id=schema.user_id, event_id=schema.event_id)

        user_event: UserEvent = UserEvent.from_orm(instance)
        return user_event

    async def get_by_event_id(self, event_id: uuid.UUID) -> uuid.UUID | None:
        """Return user event instances."""
        query: Query = select(distinct(UserEventsSchema.user_id))
        query = query.where(UserEventsSchema.event_id == event_id)
        query = query.where(UserEventsSchema.is_deleted == False)  # noqa: E712
        db_result = await self._execute(query)

        try:
            result: uuid.UUID = db_result.scalars().one_or_none()
        except MultipleResultsFound:
            raise EventError()

        return result

    async def delete_all_by_event_ids(self, event_ids: list[uuid.UUID]):
        """Delete all user events by event ids."""
        query: Query = delete(UserEventsSchema)
        query = query.where(UserEventsSchema.event_id.in_(event_ids))
        await self._execute(query)

    async def delete_all_by_events_and_user(self, event_ids: list[uuid.UUID], user_id: uuid.UUID):
        """Delete all user events by event ids."""
        query: Query = delete(UserEventsSchema)
        query = query.where(UserEventsSchema.event_id.in_(event_ids))
        query = query.where(UserEventsSchema.user_id == user_id)
        await self._execute(query)


class ActivityEventsCRUD(BaseCRUD[ActivityEventsSchema]):
    schema_class = ActivityEventsSchema

    async def save(self, schema: ActivityEventCreate) -> ActivityEvent:
        """Return activity event instance and the created information."""

        try:
            instance: ActivityEventsSchema = await self._create(ActivityEventsSchema(**schema.dict()))
        except IntegrityError:
            raise ActivityEventAlreadyExists(activity_id=schema.activity_id, event_id=schema.event_id)

        activity_event: ActivityEvent = ActivityEvent.from_orm(instance)
        return activity_event

    async def get_by_event_id(self, event_id: uuid.UUID) -> uuid.UUID | None:
        """Return activity event instances."""
        query: Query = select(ActivityEventsSchema.activity_id)
        query = query.where(ActivityEventsSchema.event_id == event_id)
        query = query.where(
            ActivityEventsSchema.is_deleted == False  # noqa: E712
        )
        result = await self._execute(query)

        try:
            activity_id = result.scalars().one_or_none()
        except MultipleResultsFound:
            raise EventError()
        return activity_id

    async def delete_all_by_event_ids(self, event_ids: list[uuid.UUID]):
        """Delete all activity events by event ids."""
        query: Query = delete(ActivityEventsSchema)
        query = query.where(ActivityEventsSchema.event_id.in_(event_ids))
        await self._execute(query)

    async def count_by_applet(self, applet_id: uuid.UUID) -> list[ActivityEventCount]:
        """Return activity ids with event count."""

        query: Query = select(
            ActivitySchema.id,
            func.count(ActivityEventsSchema.event_id).label("count"),
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
        query = query.join(EventSchema, ActivityEventsSchema.event_id == EventSchema.id)
        query = query.join(
            PeriodicitySchema,
            EventSchema.periodicity_id == PeriodicitySchema.id,
        )

        query = query.filter(ActivitySchema.is_deleted == False)  # noqa: E712
        query = query.filter(ActivitySchema.applet_id == applet_id)
        query = query.filter(PeriodicitySchema.type != PeriodicityType.ALWAYS)
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

    async def count_by_activity(self, activity_id: uuid.UUID, respondent_id: uuid.UUID | None) -> int:
        """Return event count."""

        query: Query = select(
            func.count(ActivityEventsSchema.event_id).label("count"),
        )
        query = query.join(
            UserEventsSchema,
            UserEventsSchema.event_id == ActivityEventsSchema.event_id,
            isouter=True,
        )
        query = query.filter(ActivityEventsSchema.activity_id == activity_id)
        query = query.filter(
            ActivityEventsSchema.is_deleted == False  # noqa: E712
        )
        query = query.filter(UserEventsSchema.user_id == respondent_id)
        result = await self._execute(query)

        count: int = result.scalar()
        return count

    async def get_by_event_ids(self, event_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        """Return activity event instances."""
        query: Query = select(distinct(ActivityEventsSchema.activity_id))
        query = query.where(ActivityEventsSchema.event_id.in_(event_ids))
        result = await self._execute(query)
        activity_ids = result.scalars().all()
        return activity_ids

    async def get_by_applet_id(self, applet_id: uuid.UUID) -> list[ActivityEvent]:
        """Return activity event instances."""
        query: Query = select(ActivityEventsSchema)
        query = query.join(EventSchema, ActivityEventsSchema.event_id == EventSchema.id)
        query = query.where(EventSchema.applet_id == applet_id)
        result = await self._execute(query)
        activity_events = result.scalars().all()

        return [ActivityEvent.from_orm(activity_event) for activity_event in activity_events]

    async def get_by_applet_and_user_id(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> list[ActivityEvent]:
        """Return activity event instances."""
        query: Query = select(ActivityEventsSchema)
        query = query.join(EventSchema, ActivityEventsSchema.event_id == EventSchema.id)
        query = query.join(UserEventsSchema, EventSchema.id == UserEventsSchema.event_id)
        query = query.join(
            ActivitySchema,
            ActivityEventsSchema.activity_id == ActivitySchema.id,
        )
        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(UserEventsSchema.user_id == user_id)
        result = await self._execute(query)
        activity_events = result.scalars().all()

        return [ActivityEvent.from_orm(activity_event) for activity_event in activity_events]

    async def get_missing_events(self, activity_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        query: Query = select(ActivityEventsSchema.activity_id)
        query.join(
            ActivitySchema,
            and_(
                ActivitySchema.id == ActivityEventsSchema.activity_id,
                ActivitySchema.is_reviewable.is_(False),
            ),
        )
        query.where(ActivityEventsSchema.activity_id.in_(activity_ids))
        res = await self._execute(query)
        db_result = res.scalars().all()
        return list(set(activity_ids) - set(db_result))


class FlowEventsCRUD(BaseCRUD[FlowEventsSchema]):
    schema_class = FlowEventsSchema

    async def save(self, schema: FlowEventCreate) -> FlowEvent:
        """Return flow event instance and the created information."""
        try:
            instance: FlowEventsSchema = await self._create(FlowEventsSchema(**schema.dict()))
        except IntegrityError:
            raise FlowEventAlreadyExists(flow_id=schema.flow_id, event_id=schema.event_id)

        flow_event: FlowEvent = FlowEvent.from_orm(instance)
        return flow_event

    async def get_by_event_id(self, event_id: uuid.UUID) -> uuid.UUID | None:
        """Return flow event instances."""
        query: Query = select(FlowEventsSchema.flow_id)
        query = query.where(FlowEventsSchema.event_id == event_id)
        query = query.where(FlowEventsSchema.is_deleted == False)  # noqa: E712
        result = await self._execute(query)

        try:
            flow_id: uuid.UUID = result.scalars().one_or_none()
        except MultipleResultsFound:
            raise EventError(message=f"Event{event_id} is used in multiple flows".format(event_id=event_id))

        return flow_id

    async def delete_all_by_event_ids(self, event_ids: list[uuid.UUID]):
        """Delete all flow events by event ids."""
        query: Query = delete(FlowEventsSchema)
        query = query.where(FlowEventsSchema.event_id.in_(event_ids))
        await self._execute(query)

    async def count_by_applet(self, applet_id: uuid.UUID) -> list[FlowEventCount]:
        """Return flow ids with event count."""

        query: Query = select(
            ActivityFlowSchema.id,
            func.count(FlowEventsSchema.id).label("count"),
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
        query = query.join(EventSchema, FlowEventsSchema.event_id == EventSchema.id)
        query = query.join(
            PeriodicitySchema,
            EventSchema.periodicity_id == PeriodicitySchema.id,
        )

        query = query.filter(ActivityFlowSchema.applet_id == applet_id)
        query = query.filter(
            ActivityFlowSchema.is_deleted == False  # noqa: E712
        )
        query = query.filter(PeriodicitySchema.type != PeriodicityType.ALWAYS)
        query = query.group_by(ActivityFlowSchema.applet_id, ActivityFlowSchema.id)
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

    async def get_by_event_ids(self, event_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        """Return flow event instances."""
        query: Query = select(distinct(FlowEventsSchema.flow_id))
        query = query.where(FlowEventsSchema.event_id.in_(event_ids))
        result = await self._execute(query)
        flow_ids = result.scalars().all()
        return flow_ids

    async def count_by_flow(self, flow_id: uuid.UUID, respondent_id: uuid.UUID | None) -> int:
        """Return event count."""

        query: Query = select(
            func.count(FlowEventsSchema.event_id).label("count"),
        )
        query = query.join(
            UserEventsSchema,
            FlowEventsSchema.event_id == UserEventsSchema.event_id,
            isouter=True,
        )
        query = query.filter(FlowEventsSchema.flow_id == flow_id)
        query = query.filter(
            FlowEventsSchema.is_deleted == False  # noqa: E712
        )
        query = query.filter(UserEventsSchema.user_id == respondent_id)
        result = await self._execute(query)

        count: int = result.scalar()
        return count

    async def get_by_applet_id(self, applet_id: uuid.UUID) -> list[FlowEvent]:
        """Return flow event instances."""
        query: Query = select(FlowEventsSchema)
        query = query.join(EventSchema, FlowEventsSchema.event_id == EventSchema.id)
        query = query.where(EventSchema.applet_id == applet_id)
        result = await self._execute(query)
        flow_events = result.scalars().all()

        return [FlowEvent.from_orm(flow_event) for flow_event in flow_events]

    async def get_by_applet_and_user_id(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> list[FlowEvent]:
        """Return flow event instances."""
        query: Query = select(FlowEventsSchema)
        query = query.join(EventSchema, FlowEventsSchema.event_id == EventSchema.id)
        query = query.join(UserEventsSchema, EventSchema.id == UserEventsSchema.event_id)
        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(UserEventsSchema.user_id == user_id)
        result = await self._execute(query)
        flow_events = result.scalars().all()

        return [FlowEvent.from_orm(flow_event) for flow_event in flow_events]
