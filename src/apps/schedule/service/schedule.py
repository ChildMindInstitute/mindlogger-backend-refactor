import uuid

from apps.activities.crud import ActivitiesCRUD
from apps.activity_flows.crud import FlowsCRUD
from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.schedule.crud.events import (
    ActivityEventsCRUD,
    EventCRUD,
    FlowEventsCRUD,
    UserEventsCRUD,
)
from apps.schedule.crud.periodicity import PeriodicityCRUD
from apps.schedule.db.schemas import EventSchema
from apps.schedule.domain.constants import (
    AvailabilityType,
    DefaultEvent,
    PeriodicityType,
    TimerType,
)
from apps.schedule.domain.schedule.internal import (
    ActivityEventCreate,
    Event,
    EventCreate,
    EventFull,
    EventUpdate,
    FlowEventCreate,
    Periodicity,
    UserEventCreate,
)
from apps.schedule.domain.schedule.public import (
    EventAvailabilityDto,
    HourMinute,
    PublicEvent,
    PublicEventByUser,
    PublicEventCount,
    PublicPeriodicity,
    ScheduleEventDto,
    TimerDto,
)
from apps.schedule.domain.schedule.requests import EventRequest
from apps.shared.errors import NotFoundError
from apps.shared.query_params import QueryParams
from apps.workspaces.domain.constants import Role

__all__ = ["ScheduleService"]


class ScheduleService:
    def __init__(self):
        pass

    async def create_schedule(
        self, schedule: EventRequest, applet_id: uuid.UUID
    ) -> PublicEvent:
        # Delete all events of this activity or flow
        # if new periodicity type is "always"

        if schedule.periodicity.type == PeriodicityType.always:
            await self._delete_by_activity_or_flow(
                applet_id=applet_id,
                activity_id=schedule.activity_id,
                flow_id=schedule.flow_id,
            )

        # Validate schedule data before saving
        await self._validate_schedule(applet_id=applet_id, schedule=schedule)

        # Create periodicity
        periodicity: Periodicity = await PeriodicityCRUD().save(
            schedule.periodicity
        )

        # Create event
        event: Event = await EventCRUD().save(
            EventCreate(
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                all_day=schedule.all_day,
                access_before_schedule=schedule.access_before_schedule,
                one_time_completion=schedule.one_time_completion,
                timer=schedule.timer,
                timer_type=schedule.timer_type,
                periodicity_id=periodicity.id,
                applet_id=applet_id,
            )
        )

        # Create event-user
        if schedule.user_id:
            await UserEventsCRUD().save(
                UserEventCreate(event_id=event.id, user_id=schedule.user_id)
            )
        # Create event-activity or event-flow
        if schedule.activity_id:
            await ActivityEventsCRUD().save(
                ActivityEventCreate(
                    event_id=event.id, activity_id=schedule.activity_id
                )
            )
        else:
            await FlowEventsCRUD().save(
                FlowEventCreate(event_id=event.id, flow_id=schedule.flow_id)
            )

        return PublicEvent(
            **event.dict(),
            periodicity=PublicPeriodicity(**periodicity.dict()),
            user_id=schedule.user_id,
            activity_id=schedule.activity_id,
            flow_id=schedule.flow_id,
        )

    async def get_schedule_by_id(self, schedule_id: uuid.UUID) -> PublicEvent:
        event: Event = await EventCRUD().get_by_id(pk=schedule_id)
        periodicity: Periodicity = await PeriodicityCRUD().get_by_id(
            event.periodicity_id
        )
        user_id = await UserEventsCRUD().get_by_event_id(event_id=event.id)
        activity_id = await ActivityEventsCRUD().get_by_event_id(
            event_id=event.id
        )
        flow_id = await FlowEventsCRUD().get_by_event_id(event_id=event.id)

        return PublicEvent(
            **event.dict(),
            periodicity=PublicPeriodicity(**periodicity.dict()),
            user_id=user_id,
            activity_id=activity_id,
            flow_id=flow_id,
        )

    async def get_all_schedules(
        self, applet_id: uuid.UUID
    ) -> list[PublicEvent]:
        event_schemas: list[
            EventSchema
        ] = await EventCRUD().get_all_by_applet_id(applet_id)
        events: list[PublicEvent] = []

        for event_schema in event_schemas:

            event: Event = Event.from_orm(event_schema)

            periodicity: Periodicity = await PeriodicityCRUD().get_by_id(
                event.periodicity_id
            )
            user_id = await UserEventsCRUD().get_by_event_id(event_id=event.id)
            activity_id = await ActivityEventsCRUD().get_by_event_id(
                event_id=event.id
            )
            flow_id = await FlowEventsCRUD().get_by_event_id(event_id=event.id)

            events.append(
                PublicEvent(
                    **event.dict(),
                    periodicity=PublicPeriodicity(**periodicity.dict()),
                    user_id=user_id,
                    activity_id=activity_id,
                    flow_id=flow_id,
                )
            )

        return events

    async def delete_all_schedules(self, applet_id: uuid.UUID):
        event_schemas: list[
            EventSchema
        ] = await EventCRUD().get_all_by_applet_id(applet_id)
        event_ids = [event_schema.id for event_schema in event_schemas]
        periodicity_ids = [
            event_schema.periodicity_id for event_schema in event_schemas
        ]
        if not event_ids:
            raise NotFoundError(
                message=f"No schedules found for applet {applet_id}"
            )

        # Get all activity_ids and flow_ids
        activity_ids = await ActivityEventsCRUD().get_by_event_ids(event_ids)
        flow_ids = await FlowEventsCRUD().get_by_event_ids(event_ids)

        await UserEventsCRUD().delete_all_by_event_ids(event_ids)
        await ActivityEventsCRUD().delete_all_by_event_ids(event_ids)
        await FlowEventsCRUD().delete_all_by_event_ids(event_ids)
        await PeriodicityCRUD().delete_by_ids(periodicity_ids)
        await EventCRUD().delete_by_applet_id(applet_id)

        # Create default events for activities and flows
        for activity_id in activity_ids:
            await self._create_default_event(
                applet_id=applet_id, activity_id=activity_id, is_activity=True
            )
        for flow_id in flow_ids:
            await self._create_default_event(
                applet_id=applet_id, activity_id=flow_id, is_activity=False
            )

    async def delete_schedule_by_id(self, schedule_id: uuid.UUID):
        event: Event = await EventCRUD().get_by_id(pk=schedule_id)
        periodicity_id = event.periodicity_id

        # Get activity_id or flow_id if exists
        activity_id = await ActivityEventsCRUD().get_by_event_id(
            event_id=schedule_id
        )
        flow_id = await FlowEventsCRUD().get_by_event_id(event_id=schedule_id)

        # Delete event-user, event-activity, event-flow
        await UserEventsCRUD().delete_all_by_event_ids(event_ids=[schedule_id])
        await ActivityEventsCRUD().delete_all_by_event_ids(
            event_ids=[schedule_id]
        )
        await FlowEventsCRUD().delete_all_by_event_ids(event_ids=[schedule_id])
        await PeriodicityCRUD().delete_by_ids([periodicity_id])
        await EventCRUD().delete_by_id(pk=schedule_id)

        # Create default event for activity or flow if another event doesn't exist # noqa: E501
        if activity_id:
            count_events = await ActivityEventsCRUD().count_by_activity(
                activity_id=activity_id
            )
            if count_events == 0:
                await self._create_default_event(
                    applet_id=event.applet_id,
                    activity_id=activity_id,
                    is_activity=True,
                )

        elif flow_id:
            count_events = await FlowEventsCRUD().count_by_flow(
                flow_id=flow_id
            )
            if count_events == 0:
                await self._create_default_event(
                    applet_id=event.applet_id,
                    activity_id=flow_id,
                    is_activity=False,
                )

    async def update_schedule(
        self,
        applet_id: uuid.UUID,
        schedule_id: uuid.UUID,
        schedule: EventRequest,
    ) -> PublicEvent:
        # Delete all events of this activity or flow
        # if new periodicity type is "always"

        if schedule.periodicity.type == PeriodicityType.always:
            await self._delete_by_activity_or_flow(
                applet_id=applet_id,
                activity_id=schedule.activity_id,
                flow_id=schedule.flow_id,
            )

        event: Event = await EventCRUD().get_by_id(pk=schedule_id)

        await self._validate_schedule(applet_id=applet_id, schedule=schedule)

        # Update periodicity
        periodicity: Periodicity = await PeriodicityCRUD().get_by_id(
            event.periodicity_id
        )
        periodicity = await PeriodicityCRUD().update(
            pk=periodicity.id, schema=schedule.periodicity
        )

        # Update event
        event = await EventCRUD().update(
            pk=schedule_id,
            schema=EventUpdate(
                start_time=schedule.start_time,
                end_time=schedule.end_time,
                all_day=schedule.all_day,
                access_before_schedule=schedule.access_before_schedule,
                one_time_completion=schedule.one_time_completion,
                timer=schedule.timer,
                timer_type=schedule.timer_type,
                periodicity_id=periodicity.id,
                applet_id=applet_id,
            ),
        )

        # Update event-user
        await UserEventsCRUD().delete_all_by_event_ids(event_ids=[schedule_id])
        if schedule.user_id:
            await UserEventsCRUD().save(
                UserEventCreate(event_id=event.id, user_id=schedule.user_id)
            )

        # Update event-activity or event-flow
        await ActivityEventsCRUD().delete_all_by_event_ids(
            event_ids=[schedule_id]
        )
        await FlowEventsCRUD().delete_all_by_event_ids(event_ids=[schedule_id])
        if schedule.activity_id:
            await ActivityEventsCRUD().save(
                ActivityEventCreate(
                    event_id=event.id, activity_id=schedule.activity_id
                )
            )
        else:
            await FlowEventsCRUD().save(
                FlowEventCreate(event_id=event.id, flow_id=schedule.flow_id)
            )

        return PublicEvent(
            **event.dict(),
            periodicity=PublicPeriodicity(**periodicity.dict()),
            user_id=schedule.user_id,
            activity_id=schedule.activity_id,
            flow_id=schedule.flow_id,
        )

    async def _validate_schedule(
        self, applet_id: uuid.UUID, schedule: EventRequest
    ) -> None:
        """Validate schedule before saving it to the database."""
        # Check if user has access to applet
        if schedule.user_id:
            user_applet_access = await (
                UserAppletAccessCRUD().get_by_applet_and_user_as_respondent(
                    applet_id=applet_id, user_id=schedule.user_id
                )
            )  # noqa: E501
            if not user_applet_access:
                raise NotFoundError(
                    message=f"User {schedule.user_id} "
                    f"does not have access to applet {applet_id}"
                )  # noqa: E501

        # Check if activity or flow exists inside applet
        activity_or_flow = None
        if schedule.activity_id:
            activity_or_flow = (
                await ActivitiesCRUD().get_by_applet_id_and_activity_id(
                    applet_id=applet_id, activity_id=schedule.activity_id
                )
            )
        if schedule.flow_id:
            activity_or_flow = await FlowsCRUD().get_by_applet_id_and_flow_id(
                applet_id=applet_id, flow_id=schedule.flow_id
            )
        if not activity_or_flow:
            raise NotFoundError(
                message=f"Activity or flow with id "
                f"{schedule.activity_id or schedule.flow_id}"
                f" not found inside applet {applet_id}"
            )  # noqa: E501

    async def count_schedules(self, applet_id: uuid.UUID) -> PublicEventCount:

        event_count = PublicEventCount(activity_events=[], flow_events=[])

        # Get list of activity-event ids
        activity_counts = await ActivityEventsCRUD().count_by_applet(
            applet_id=applet_id
        )

        # Get list of flow-event ids
        flow_counts = await FlowEventsCRUD().count_by_applet(
            applet_id=applet_id
        )

        event_count.activity_events = (
            activity_counts if activity_counts else []
        )
        event_count.flow_events = flow_counts if flow_counts else []

        return event_count

    async def delete_by_user_id(self, applet_id, user_id):
        # Get list of event_ids for user and delete them all

        event_schemas = await EventCRUD().get_all_by_applet_and_user(
            applet_id, user_id
        )
        event_ids = [event_schema.id for event_schema in event_schemas]
        periodicity_ids = [
            event_schema.periodicity.id for event_schema in event_schemas
        ]
        if not event_ids:
            raise NotFoundError(
                message=f"No schedules found in applet "
                f"{applet_id} for user {user_id}"
            )  # noqa: E501

        await UserEventsCRUD().delete_all_by_events_and_user(
            event_ids, user_id
        )
        await ActivityEventsCRUD().delete_all_by_event_ids(event_ids)
        await FlowEventsCRUD().delete_all_by_event_ids(event_ids)
        await PeriodicityCRUD().delete_by_ids(periodicity_ids)
        await EventCRUD().delete_by_ids(event_ids)

    async def _create_default_event(
        self, applet_id: uuid.UUID, activity_id: uuid.UUID, is_activity: bool
    ) -> None:
        """Create default schedules for applet."""
        default_event = DefaultEvent()
        if is_activity:
            default_event.activity_id = activity_id
        else:
            default_event.flow_id = activity_id

        # Create default event
        await self.create_schedule(
            applet_id=applet_id, schedule=EventRequest(**default_event.dict())
        )

    async def _delete_by_activity_or_flow(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID | None,
        flow_id: uuid.UUID | None,
    ) -> None:
        """Delete schedules by activity or flow id."""
        event_schemas = []

        if activity_id:
            # Get list of event_ids for activity and delete them all
            event_schemas = await EventCRUD().get_all_by_applet_and_activity(
                applet_id, activity_id
            )
        elif flow_id:
            # Get list of event_ids for flow and delete them all
            event_schemas = await EventCRUD().get_all_by_applet_and_flow(
                applet_id, flow_id
            )
        event_ids = [event_schema.id for event_schema in event_schemas]

        periodicity_ids = [
            event_schema.periodicity_id for event_schema in event_schemas
        ]
        if event_ids:
            await UserEventsCRUD().delete_all_by_event_ids(event_ids)
            await ActivityEventsCRUD().delete_all_by_event_ids(event_ids)
            await FlowEventsCRUD().delete_all_by_event_ids(event_ids)
            await PeriodicityCRUD().delete_by_ids(periodicity_ids)
            await EventCRUD().delete_by_ids(event_ids)

    async def delete_by_activity_ids(
        self, applet_id: uuid.UUID, activity_ids: list[uuid.UUID]
    ) -> None:
        """Delete schedules by activity id."""
        for activity_id in activity_ids:
            await self._delete_by_activity_or_flow(
                applet_id=applet_id, activity_id=activity_id, flow_id=None
            )

    async def delete_by_flow_ids(
        self, applet_id: uuid.UUID, flow_ids: list[uuid.UUID]
    ) -> None:
        """Delete schedules by flow id."""
        for flow_id in flow_ids:
            await self._delete_by_activity_or_flow(
                applet_id=applet_id, activity_id=None, flow_id=flow_id
            )

    async def create_default_schedules(
        self,
        applet_id: uuid.UUID,
        activity_ids: list[uuid.UUID],
        is_activity: bool,
    ) -> None:
        """Create default schedules for applet."""
        for activity_id in activity_ids:
            await self._create_default_event(
                applet_id=applet_id,
                activity_id=activity_id,
                is_activity=is_activity,
            )

    async def get_events_by_user(
        self, user_id: uuid.UUID
    ) -> list[PublicEventByUser]:
        """Get all events for user in applets that user is respondent."""
        applets = await AppletsCRUD().get_applets_by_roles(
            user_id=user_id,
            roles=[
                Role.RESPONDENT,
            ],
            query_params=QueryParams(),
        )
        applet_ids = [applet.id for applet in applets]
        events = []

        for applet_id in applet_ids:
            user_events: list = await EventCRUD().get_all_by_applet_and_user(
                applet_id=applet_id,
                user_id=user_id,
            )
            general_events: list = (
                await EventCRUD().get_general_events_by_user(
                    applet_id=applet_id, user_id=user_id
                )
            )
            all_events = user_events + general_events
            events.append(
                PublicEventByUser(
                    applet_id=applet_id,
                    events=[
                        self._convert_to_dto(event=event)
                        for event in all_events
                    ],
                )
            )

        return events

    def _convert_to_dto(self, event: EventFull) -> ScheduleEventDto:
        """Convert event to dto."""
        return ScheduleEventDto(
            id=event.id,
            entityId=event.activity_id if event.activity_id else event.flow_id,
            timers=TimerDto(
                timer=HourMinute(
                    hours=event.timer.seconds // 3600,
                    minutes=event.timer.seconds // 60 % 60,
                )
                if event.timer_type == TimerType.timer
                else None,
                idleTimer=HourMinute(
                    hours=event.timer.seconds // 3600,
                    minutes=event.timer.seconds // 60 % 60,
                )
                if event.timer_type == TimerType.idle
                else None,
            ),
            availabilityType=AvailabilityType.AlwaysAvailable
            if event.periodicity.type == PeriodicityType.always
            else AvailabilityType.ScheduledAccess,
            availability=EventAvailabilityDto(
                oneTimeCompletion=event.one_time_completion,
                periodicityType=event.periodicity.type,
                timeFrom=HourMinute(
                    hours=event.start_time.hour,
                    minutes=event.start_time.minute,
                ),
                timeTo=HourMinute(
                    hours=event.end_time.hour, minutes=event.end_time.minute
                ),
                allowAccessBeforeFromTime=event.access_before_schedule,
                startDate=event.periodicity.start_date,
                endDate=event.periodicity.end_date,
            ),
        )

    async def get_events_by_user_and_applet(
        self, user_id: uuid.UUID, applet_id: uuid.UUID
    ) -> PublicEventByUser:
        """Get all events for user in applet."""

        applet = await AppletsCRUD().get_applet_by_roles(
            user_id=user_id,
            applet_id=applet_id,
            roles=[
                Role.RESPONDENT,
            ],
        )

        if not applet:
            raise NotFoundError(
                message=f"User {user_id} "
                f"does not have access to applet {applet_id}"
            )

        user_events: list = await EventCRUD().get_all_by_applet_and_user(
            applet_id=applet_id,
            user_id=user_id,
        )

        general_events: list = await EventCRUD().get_general_events_by_user(
            applet_id=applet_id, user_id=user_id
        )
        all_events = user_events + general_events

        events = PublicEventByUser(
            applet_id=applet_id,
            events=[self._convert_to_dto(event=event) for event in all_events],
        )

        print(events)
        return events
