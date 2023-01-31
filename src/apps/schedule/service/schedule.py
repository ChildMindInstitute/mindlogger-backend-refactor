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
from apps.schedule.domain.schedule.internal import (
    ActivityEventCreate,
    Event,
    EventCreate,
    FlowEventCreate,
    Periodicity,
    UserEventCreate,
)
from apps.schedule.domain.schedule.public import PublicEvent, PublicPeriodicity
from apps.schedule.domain.schedule.requests import EventRequest
from apps.shared.errors import NotFoundError

__all__ = ["ScheduleService"]


class ScheduleService:
    def __init__(self):
        pass

    async def create_schedule(
        self, schedule: EventRequest, applet_id: int
    ) -> PublicEvent:
        # Check if user has access to applet
        if schedule.user_ids:
            for user_id in schedule.user_ids:
                user_applet_access = await UserAppletAccessCRUD().get_by_applet_and_user_as_respondent(  # noqa: E501
                    applet_id=applet_id, user_id=user_id
                )
                if not user_applet_access:
                    raise NotFoundError(
                        f"User {user_id} does not have access to applet {applet_id}"  # noqa: E501
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
                f"Activity or flow with id {schedule.activity_id or schedule.flow_id} not found inside applet {applet_id}"  # noqa: E501
            )

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
        if schedule.user_ids:
            for user_id in schedule.user_ids:
                await UserEventsCRUD().save(
                    UserEventCreate(event_id=event.id, user_id=user_id)
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
            user_ids=schedule.user_ids,
            activity_id=schedule.activity_id,
            flow_id=schedule.flow_id,
        )

    def update_schedule(self, schedule):
        pass

    def delete_schedule(self, schedule):
        pass

    async def get_schedule_by_id(self, schedule_id: int) -> PublicEvent:
        event: Event = await EventCRUD().get_by_id(id=schedule_id)
        periodicity: Periodicity = await PeriodicityCRUD().get_by_id(
            event.periodicity_id
        )
        users: list[int] = await UserEventsCRUD().get_by_event_id(
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
            user_ids=users,
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
            users: list[int] = await UserEventsCRUD().get_by_event_id(
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
                    user_ids=users,
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
            raise NotFoundError(f"No schedules found for applet {applet_id}")

        await UserEventsCRUD().delete_all_by_event_ids(event_ids)
        await ActivityEventsCRUD().delete_all_by_event_ids(event_ids)
        await FlowEventsCRUD().delete_all_by_event_ids(event_ids)
        await PeriodicityCRUD().delete_all_by_ids(periodicity_ids)
        await EventCRUD().delete_all_by_ids(applet_id)

    async def delete_schedule_by_id(self, schedule_id: int):
        event: Event = await EventCRUD().get_by_id(id=schedule_id)
        periodicity_id: int = event.periodicity_id
        if not event:
            raise NotFoundError(f"No schedule found with id {schedule_id}")

        await UserEventsCRUD().delete_all_by_event_ids(event_ids=[schedule_id])
        await ActivityEventsCRUD().delete_all_by_event_ids(
            event_ids=[schedule_id]
        )
        await FlowEventsCRUD().delete_all_by_event_ids(event_ids=[schedule_id])
        await PeriodicityCRUD().delete_all_by_ids([periodicity_id])
        await EventCRUD().delete_by_id(id=schedule_id)
