from apps.activities.crud import ActivitiesCRUD
from apps.activity_flows.crud import FlowsCRUD
from apps.applets.crud import UserAppletAccessCRUD
from apps.schedule.crud.events import (
    ActivityEventsCRUD,
    EventCRUD,
    FlowEventsCRUD,
    UserEventsCRUD,
)
from apps.schedule.crud.periodicity import PeriodicityCRUD
from apps.schedule.db.schemas import EventSchema
from apps.schedule.domain.constants import DefaultEvent, PeriodicityType
from apps.schedule.domain.schedule.internal import (
    ActivityEventCreate,
    Event,
    EventCreate,
    EventUpdate,
    FlowEventCreate,
    Periodicity,
    UserEventCreate,
)
from apps.schedule.domain.schedule.public import (
    PublicEvent,
    PublicEventCount,
    PublicPeriodicity,
)
from apps.schedule.domain.schedule.requests import EventRequest
from apps.shared.errors import NotFoundError

__all__ = ["ScheduleService"]


class ScheduleService:
    def __init__(self):
        pass

    async def create_schedule(
        self, schedule: EventRequest, applet_id: int
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

    async def get_schedule_by_id(self, schedule_id: int) -> PublicEvent:
        event: Event = await EventCRUD().get_by_id(pk=schedule_id)
        periodicity: Periodicity = await PeriodicityCRUD().get_by_id(
            event.periodicity_id
        )
        user_id: int = await UserEventsCRUD().get_by_event_id(
            event_id=event.id
        )
        activity_id: int = await ActivityEventsCRUD().get_by_event_id(
            event_id=event.id
        )
        flow_id: int = await FlowEventsCRUD().get_by_event_id(
            event_id=event.id
        )

        return PublicEvent(
            **event.dict(),
            periodicity=PublicPeriodicity(**periodicity.dict()),
            user_id=user_id,
            activity_id=activity_id,
            flow_id=flow_id,
        )

    async def get_all_schedules(self, applet_id: int) -> list[PublicEvent]:
        event_schemas: list[
            EventSchema
        ] = await EventCRUD().get_all_by_applet_id(applet_id)
        events: list[PublicEvent] = []

        for event_schema in event_schemas:

            event: Event = Event.from_orm(event_schema)

            periodicity: Periodicity = await PeriodicityCRUD().get_by_id(
                event.periodicity_id
            )
            user_id: int = await UserEventsCRUD().get_by_event_id(
                event_id=event.id
            )
            activity_id: int = await ActivityEventsCRUD().get_by_event_id(
                event_id=event.id
            )
            flow_id: int = await FlowEventsCRUD().get_by_event_id(
                event_id=event.id
            )

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

    async def delete_all_schedules(self, applet_id: int):
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
        activity_ids: list[int] = await ActivityEventsCRUD().get_by_event_ids(
            event_ids
        )
        flow_ids: list[int] = await FlowEventsCRUD().get_by_event_ids(
            event_ids
        )

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

    async def delete_schedule_by_id(self, schedule_id: int):
        event: Event = await EventCRUD().get_by_id(pk=schedule_id)
        periodicity_id: int = event.periodicity_id

        # Get activity_id or flow_id if exists
        activity_id: int = await ActivityEventsCRUD().get_by_event_id(
            event_id=schedule_id
        )
        flow_id: int = await FlowEventsCRUD().get_by_event_id(
            event_id=schedule_id
        )

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
        self, applet_id: int, schedule_id: int, schedule: EventRequest
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
        self, applet_id: int, schedule: EventRequest
    ) -> None:
        """Validate schedule before saving it to the database."""
        # Check if user has access to applet
        if schedule.user_id:
            user_applet_access = await UserAppletAccessCRUD().get_by_applet_and_user_as_respondent(  # noqa: E501
                applet_id=applet_id, user_id=schedule.user_id
            )
            if not user_applet_access:
                raise NotFoundError(
                    message=f"User {schedule.user_id} does not have access to applet {applet_id}"  # noqa: E501
                )

        # Check if activity or flow exists inside applet
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
                message=f"Activity or flow with id {schedule.activity_id or schedule.flow_id} not found inside applet {applet_id}"  # noqa: E501
            )

    async def count_schedules(self, applet_id: int) -> PublicEventCount:

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
            event_schema.periodicity_id for event_schema in event_schemas
        ]
        if not event_ids:
            raise NotFoundError(
                message=f"No schedules found in applet {applet_id} for user {user_id}"  # noqa: E501
            )

        await UserEventsCRUD().delete_all_by_events_and_user(
            event_ids, user_id
        )
        await ActivityEventsCRUD().delete_all_by_event_ids(event_ids)
        await FlowEventsCRUD().delete_all_by_event_ids(event_ids)
        await PeriodicityCRUD().delete_by_ids(periodicity_ids)
        await EventCRUD().delete_by_ids(event_ids)

    async def _create_default_event(
        self, applet_id: int, activity_id: int, is_activity: bool
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
        self, applet_id: int, activity_id: int | None, flow_id: int | None
    ) -> None:
        """Delete schedules by activity or flow id."""
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
        self, applet_id: int, activity_ids: list[int]
    ) -> None:
        """Delete schedules by activity id."""
        for activity_id in activity_ids:
            await self._delete_by_activity_or_flow(
                applet_id=applet_id, activity_id=activity_id, flow_id=None
            )

    async def delete_by_flow_ids(
        self, applet_id: int, flow_ids: list[int]
    ) -> None:
        """Delete schedules by flow id."""
        for flow_id in flow_ids:
            await self._delete_by_activity_or_flow(
                applet_id=applet_id, activity_id=None, flow_id=flow_id
            )

    async def create_default_schedules(
        self, applet_id: int, activity_ids: list[int], is_activity: bool
    ) -> None:
        """Create default schedules for applet."""
        for activity_id in activity_ids:
            await self._create_default_event(
                applet_id=applet_id,
                activity_id=activity_id,
                is_activity=is_activity,
            )
