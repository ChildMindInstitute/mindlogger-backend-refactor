import uuid
from datetime import date

from sqlalchemy import Integer, update
from sqlalchemy.exc import IntegrityError, MultipleResultsFound, NoResultFound
from sqlalchemy.orm import Query
from sqlalchemy.sql import and_, delete, func, or_, select
from sqlalchemy.sql.expression import case, cast

from apps.activities.db.schemas import ActivitySchema
from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.schedule.db.schemas import (
    EventSchema,
)
from apps.schedule.domain.constants import EventType, PeriodicityType
from apps.schedule.domain.schedule.internal import (
    Event,
    EventCreate,
    EventFull,
    EventUpdate,
)
from apps.schedule.domain.schedule.public import ActivityEventCount, FlowEventCount
from apps.schedule.errors import (
    EventError,
    EventNotFoundError,
)
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.database import BaseCRUD

__all__ = ["EventCRUD"]


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
        query = query.where(EventSchema.applet_id == applet_id)
        query = query.where(EventSchema.is_deleted.is_(False))
        if respondent_id:
            query = query.where(EventSchema.user_id == respondent_id)
        else:
            query = query.where(EventSchema.user_id.is_(None))

        result = await self._execute(query)
        return result.scalars().all()

    async def get_public_by_applet_id(self, applet_id: uuid.UUID) -> list[EventSchema]:
        """Return event instance."""
        query: Query = select(EventSchema)
        query = query.where(EventSchema.applet_id == applet_id)
        query = query.distinct(EventSchema.id)
        query = query.where(EventSchema.user_id.is_(None))
        query = query.where(EventSchema.is_deleted.is_(False))

        result = await self._execute(query)
        return result.scalars().all()

    async def update(self, pk: uuid.UUID, schema: EventUpdate) -> Event:
        """Update event by event id."""
        event_schema = EventSchema(**schema.dict())

        dict_values = dict(event_schema)

        query = (
            update(EventSchema)
            .where(EventSchema.id == pk)
            .values(
                **dict_values,
                version=func.concat(
                    func.to_char(func.current_date(), "YYYYMMDD"),
                    "-",
                    case(
                        (
                            EventSchema.version.like(func.concat(func.to_char(func.current_date(), "YYYYMMDD"), "-%")),
                            cast(func.split_part(EventSchema.version, "-", 2), Integer) + 1,
                        ),
                        else_=1,
                    ),
                ),
            )
            .returning(EventSchema)
        )

        db_result = await self._execute(query)
        rows_as_dict = db_result.mappings().all()

        if len(rows_as_dict) == 0:
            raise NoResultFound()
        elif len(rows_as_dict) > 1:
            raise MultipleResultsFound()

        return Event.from_orm(EventSchema(**rows_as_dict[0]))

    async def get_all_by_applet_and_user(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> list[EventFull]:
        """Get events by applet_id and user_id"""
        query: Query = select(EventSchema)

        query = query.where(
            EventSchema.applet_id == applet_id, EventSchema.user_id == user_id, EventSchema.is_deleted.is_(False)
        )

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
                    version=row.EventSchema.version,
                    user_id=user_id,
                    periodicity=row.EventSchema.periodicity,
                    start_date=row.EventSchema.start_date,
                    end_date=row.EventSchema.end_date,
                    selected_date=row.EventSchema.selected_date,
                    activity_id=row.EventSchema.activity_id,
                    flow_id=row.EventSchema.activity_flow_id,
                    event_type=row.EventSchema.event_type,
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

        query: Query = select(EventSchema)
        query = query.where(
            EventSchema.applet_id.in_(applet_ids),
            EventSchema.is_deleted.is_(False),
            EventSchema.user_id == user_id,
        )
        if min_end_date and max_start_date:
            query = query.where(
                or_(
                    EventSchema.periodicity == PeriodicityType.ALWAYS,
                    and_(
                        EventSchema.periodicity != PeriodicityType.ONCE,
                        or_(
                            EventSchema.start_date.is_(None),
                            EventSchema.start_date <= max_start_date,
                        ),
                        or_(
                            EventSchema.end_date.is_(None),
                            EventSchema.end_date >= min_end_date,
                        ),
                    ),
                    and_(
                        EventSchema.periodicity == PeriodicityType.ONCE,
                        EventSchema.selected_date <= max_start_date,
                        EventSchema.selected_date >= min_end_date,
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
                    access_before_schedule=row.EventSchema.access_before_schedule,
                    one_time_completion=row.EventSchema.one_time_completion,
                    timer=row.EventSchema.timer,
                    timer_type=row.EventSchema.timer_type,
                    version=row.EventSchema.version,
                    user_id=user_id,
                    periodicity=row.EventSchema.periodicity,
                    start_date=row.EventSchema.start_date,
                    end_date=row.EventSchema.end_date,
                    selected_date=row.EventSchema.selected_date,
                    activity_id=row.EventSchema.activity_id,
                    flow_id=row.EventSchema.activity_flow_id,
                    event_type=row.EventSchema.event_type,
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
        # select only always available if requested
        if only_always_available:
            query.where(EventSchema.periodicity == PeriodicityType.ALWAYS)
        query = query.where(
            EventSchema.applet_id == applet_id,
            EventSchema.is_deleted.is_(False),
            EventSchema.activity_id == activity_id,
            EventSchema.user_id == respondent_id,
        )

        result = await self._execute(query)
        return result.scalars().all()

    async def validate_existing_always_available(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID | None,
        flow_id: uuid.UUID | None,
        respondent_id: uuid.UUID | None,
    ) -> bool:
        """Validate if there is already an always available event."""
        query: Query = select(1)
        query = query.select_from(EventSchema)

        if activity_id:
            query = query.where(EventSchema.activity_id == activity_id)

        if flow_id:
            query = query.where(EventSchema.activity_flow_id == flow_id)

        query = query.where(
            EventSchema.periodicity == PeriodicityType.ALWAYS,
            EventSchema.applet_id == applet_id,
            EventSchema.is_deleted.is_(False),
            EventSchema.user_id == respondent_id,
        )

        query = query.limit(1)

        result = await self._execute(query)
        return result.fetchone() is not None

    async def get_all_by_applet_and_flow(
        self,
        applet_id: uuid.UUID,
        flow_id: uuid.UUID,
        respondent_id: uuid.UUID | None,
        only_always_available: bool = False,
    ) -> list[EventSchema]:
        """Get events by applet_id and flow_id"""
        query: Query = select(EventSchema)

        # select only always available if requested
        if only_always_available:
            query.where(EventSchema.periodicity == PeriodicityType.ALWAYS)

        query = query.where(
            EventSchema.applet_id == applet_id,
            EventSchema.is_deleted.is_(False),
            EventSchema.user_id == respondent_id,
            EventSchema.activity_flow_id == flow_id,
        )

        result = await self._execute(query)
        return result.scalars().all()

    async def get_general_events_by_user(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> list[EventFull]:
        """Get general events by applet_id and user_id"""

        # select flow and activity ids to exclude
        ids = (
            select(
                func.coalesce(EventSchema.activity_flow_id, EventSchema.activity_id).label("entity_id"),
            )
            .select_from(EventSchema)
            .where(EventSchema.user_id == user_id, EventSchema.applet_id == applet_id)
            .group_by("entity_id")
        )

        query: Query = select(EventSchema)
        query = query.where(
            EventSchema.applet_id == applet_id,
            EventSchema.is_deleted.is_(False),
            or_(
                EventSchema.activity_flow_id.is_(None),
                EventSchema.activity_flow_id.not_in(ids),
            ),
            or_(
                EventSchema.activity_id.is_(None),
                EventSchema.activity_id.not_in(ids),
            ),
            EventSchema.user_id.is_(None),
        )

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
                    version=row.EventSchema.version,
                    user_id=user_id,
                    periodicity=row.EventSchema.periodicity,
                    start_date=row.EventSchema.start_date,
                    end_date=row.EventSchema.end_date,
                    selected_date=row.EventSchema.selected_date,
                    activity_id=row.EventSchema.activity_id,
                    flow_id=row.EventSchema.activity_flow_id,
                    event_type=row.EventSchema.event_type,
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

        # select flow and activity ids to exclude
        ids = (
            select(
                func.coalesce(EventSchema.activity_flow_id, EventSchema.activity_id).label("entity_id"),
            )
            .select_from(EventSchema)
            .where(EventSchema.user_id == user_id, EventSchema.applet_id.in_(applet_ids))
            .group_by("entity_id")
        )

        query: Query = select(EventSchema)

        query = query.where(
            EventSchema.applet_id.in_(applet_ids),
            EventSchema.is_deleted.is_(False),
            or_(
                EventSchema.activity_flow_id.is_(None),
                EventSchema.activity_flow_id.not_in(ids),
            ),
            or_(
                EventSchema.activity_id.is_(None),
                EventSchema.activity_id.not_in(ids),
            ),
            EventSchema.user_id.is_(None),
        )
        if min_end_date and max_start_date:
            query = query.where(
                or_(
                    EventSchema.periodicity == PeriodicityType.ALWAYS,
                    and_(
                        EventSchema.periodicity != PeriodicityType.ONCE,
                        or_(
                            EventSchema.start_date.is_(None),
                            EventSchema.start_date <= max_start_date,
                        ),
                        or_(
                            EventSchema.end_date.is_(None),
                            EventSchema.end_date >= min_end_date,
                        ),
                    ),
                    and_(
                        EventSchema.periodicity == PeriodicityType.ONCE,
                        EventSchema.selected_date <= max_start_date,
                        EventSchema.selected_date >= min_end_date,
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
                    version=row.EventSchema.version,
                    user_id=user_id,
                    periodicity=row.EventSchema.periodicity,
                    start_date=row.EventSchema.start_date,
                    end_date=row.EventSchema.end_date,
                    selected_date=row.EventSchema.selected_date,
                    activity_id=row.EventSchema.activity_id,
                    flow_id=row.EventSchema.activity_flow_id,
                    event_type=row.EventSchema.event_type,
                )
            )

        return events_map, event_ids

    async def count_general_events_by_user(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """Count general events by applet_id and user_id"""

        # select flow and activity ids to exclude
        ids = (
            select(
                func.coalesce(EventSchema.activity_flow_id, EventSchema.activity_id).label("entity_id"),
            )
            .select_from(EventSchema)
            .where(EventSchema.user_id == user_id, EventSchema.applet_id == applet_id)
            .group_by("entity_id")
        )

        query: Query = select(
            func.count(EventSchema.id).label("count"),
        )

        query = query.where(
            EventSchema.applet_id == applet_id,
            EventSchema.is_deleted.is_(False),
            or_(
                EventSchema.activity_flow_id.is_(None),
                EventSchema.activity_flow_id.not_in(ids),
            ),
            or_(
                EventSchema.activity_id.is_(None),
                EventSchema.activity_id.not_in(ids),
            ),
            EventSchema.user_id.is_(None),
        )
        db_result = await self._execute(query)

        return db_result.scalar()

    async def count_individual_events_by_user(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """Count individual events by applet_id and user_id"""

        query: Query = select(func.count(EventSchema.id))
        query = query.where(
            EventSchema.applet_id == applet_id,
            EventSchema.is_deleted.is_(False),
            EventSchema.user_id == user_id,
        )
        db_result = await self._execute(query)
        return db_result.scalar()

    async def get_all_by_activity_flow_ids(
        self,
        applet_id: uuid.UUID,
        activity_ids: list[uuid.UUID],
        is_activity: bool,
    ) -> list[EventSchema]:
        """Return events for given activity ids."""
        query: Query = select(EventSchema)
        query = query.where(EventSchema.applet_id == applet_id)

        if is_activity:
            query = query.where(EventSchema.activity_id.in_(activity_ids))
        else:
            query = query.where(EventSchema.activity_flow_id.in_(activity_ids))

        result = await self._execute(query)
        events = result.scalars().all()
        return events

    async def get_default_schedule_user_ids_by_applet_id(self, applet_id: uuid.UUID) -> list[uuid.UUID]:
        """Return user ids for default schedule."""
        individual_schedule_users = select(EventSchema.user_id).where(
            EventSchema.applet_id == applet_id,
            EventSchema.is_deleted.is_(False),
            EventSchema.user_id.isnot(None),
        )

        query: Query = select(UserAppletAccessSchema.user_id.label("user_id"))
        query = query.where(UserAppletAccessSchema.applet_id == applet_id)
        query = query.where(UserAppletAccessSchema.role == Role.RESPONDENT)
        query = query.where(UserAppletAccessSchema.is_deleted.is_(False))
        query = query.where(UserAppletAccessSchema.user_id.not_in(individual_schedule_users))
        result = await self._execute(query)
        result = result.scalars().all()
        return result

    async def count_by_activity(self, activity_id: uuid.UUID, respondent_id: uuid.UUID | None) -> int:
        """Return event count."""

        query: Query = select(
            func.count(EventSchema.id).label("count"),
        )
        query = query.where(
            EventSchema.activity_id == activity_id,
            EventSchema.is_deleted.is_(False),
            EventSchema.user_id == respondent_id,
        )
        result = await self._execute(query)

        count: int = result.scalar()
        return count

    async def count_by_flow(self, flow_id: uuid.UUID, respondent_id: uuid.UUID | None) -> int:
        """Return event count."""

        query: Query = select(
            func.count(EventSchema.id).label("count"),
        )
        query = query.filter(
            EventSchema.activity_flow_id == flow_id,
            EventSchema.is_deleted.is_(False),
            EventSchema.user_id == respondent_id,
        )
        result = await self._execute(query)

        count: int = result.scalar()
        return count

    async def count_by_applet(self, applet_id: uuid.UUID) -> tuple[list[ActivityEventCount], list[FlowEventCount]]:
        """Return activity ids and flow ids with event count."""

        query: Query = select(
            ActivitySchema.id.label("activity_id"),
            ActivitySchema.name.label("activity_name"),
            ActivityFlowSchema.id.label("flow_id"),
            ActivityFlowSchema.name.label("flow_name"),
            func.count(EventSchema.id).label("count"),
        )
        query = query.select_from(EventSchema)
        query = query.join(
            ActivitySchema,
            and_(
                ActivitySchema.id == EventSchema.activity_id,
                ActivitySchema.is_deleted.is_(False),
            ),
            isouter=True,
        )
        query = query.join(
            ActivityFlowSchema,
            and_(
                ActivityFlowSchema.id == EventSchema.activity_flow_id,
                ActivityFlowSchema.is_deleted.is_(False),
            ),
            isouter=True,
        )

        query = query.where(
            EventSchema.is_deleted.is_(False),
            EventSchema.applet_id == applet_id,
            EventSchema.periodicity != PeriodicityType.ALWAYS,
        )
        query = query.group_by(EventSchema.applet_id, ActivitySchema.id, ActivityFlowSchema.id)
        result = await self._execute(query)

        activity_event_counts: list[ActivityEventCount] = []
        flow_event_counts: list[FlowEventCount] = []

        for activity_id, activity_name, flow_id, flow_name, count in result:
            if activity_id:
                activity_event_counts.append(
                    ActivityEventCount(
                        activity_id=activity_id,
                        count=count,
                        activity_name=activity_name,
                    )
                )
            if flow_id:
                flow_event_counts.append(
                    FlowEventCount(
                        flow_id=flow_id,
                        count=count,
                        flow_name=flow_name,
                    )
                )

        return activity_event_counts, flow_event_counts

    async def get_activities_without_events(self, activity_ids: list[uuid.UUID]) -> list[uuid.UUID]:
        query: Query = select(EventSchema.activity_id)
        query.join(
            ActivitySchema,
            and_(
                ActivitySchema.id == EventSchema.activity_id,
                ActivitySchema.is_reviewable.is_(False),
            ),
        )
        query.where(EventSchema.activity_id.in_(activity_ids))
        res = await self._execute(query)
        db_result = res.scalars().all()
        return list(set(activity_ids) - set(db_result))

    async def get_by_type_and_applet_id(self, applet_id: uuid.UUID, event_type: EventType) -> list[Event]:
        """Return event instances of type flow."""
        query: Query = select(EventSchema)
        query = query.where(
            EventSchema.applet_id == applet_id,
            EventSchema.event_type == event_type,
        )

        if event_type == EventType.FLOW:
            query = query.where(EventSchema.activity_flow_id.isnot(None))
        else:
            query = query.where(EventSchema.activity_id.isnot(None))

        result = await self._execute(query)
        flow_events = result.scalars().all()

        return [Event.from_orm(flow_event) for flow_event in flow_events]
