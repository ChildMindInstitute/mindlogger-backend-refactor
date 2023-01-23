from apps.schedule.domain.schedule.requests import (
    EventRequest,
    PeriodicityRequest,
)
from apps.schedule.domain.schedule.internal import (
    EventCreate,
    UserEventCreate,
    UserEvent,
    Event,
    Periodicity,
    ActivityEventCreate,
    ActivityEvent,
    FlowEvent,
    FlowEventCreate,
)
from apps.schedule.domain.schedule.public import PublicEvent, PublicPeriodicity
from apps.schedule.crud.periodicity import PeriodicityCRUD
from apps.schedule.crud.events import (
    EventCRUD,
    UserEventsCRUD,
    ActivityEventsCRUD,
    FlowEventsCRUD,
)


class ScheduleService:
    def __init__(self):
        pass

    async def create_schedule(self, schedule: EventRequest):
        # TODO: Validate user, activity and flow exist

        periodicity: Periodicity = PeriodicityCRUD().save(schedule.periodicity)
        event: Event = EventCRUD().save(
            EventCreate(**schedule.dict(), periodicity_id=periodicity.id)
        )
        if schedule.user_id:
            await UserEventsCRUD().save(
                UserEventCreate(event_id=event.id, user_id=schedule.user_id)
            )

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
        )

    def update_schedule(self, schedule):
        pass

    def delete_schedule(self, schedule):
        pass

    def get_schedule(self, schedule):
        pass
