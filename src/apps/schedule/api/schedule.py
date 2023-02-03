from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.schedule.domain.schedule.public import PublicEvent, PublicEventCount
from apps.schedule.domain.schedule.requests import EventRequest
from apps.schedule.service.schedule import ScheduleService
from apps.shared.domain import Response, ResponseMulti
from apps.users.domain import User


async def schedule_create(
    applet_id: int,
    user: User = Depends(get_current_user),
    schema: EventRequest = Body(...),
) -> Response[PublicEvent]:

    schedule = await ScheduleService().create_schedule(schema, applet_id)
    return Response(result=PublicEvent(**schedule.dict()))


async def schedule_get_by_id(
    applet_id: int,
    schedule_id: int,
    user: User = Depends(get_current_user),
) -> Response[PublicEvent]:
    schedule = await ScheduleService().get_schedule_by_id(schedule_id)
    return Response(result=PublicEvent(**schedule.dict()))


async def schedule_get_all(
    applet_id: int,
    user: User = Depends(get_current_user),
) -> ResponseMulti[PublicEvent]:
    schedules = await ScheduleService().get_all_schedules(applet_id)

    return ResponseMulti(result=schedules)


async def schedule_delete_all(
    applet_id: int,
    user: User = Depends(get_current_user),
):
    await ScheduleService().delete_all_schedules(applet_id)


async def schedule_delete_by_id(
    applet_id: int,
    schedule_id: int,
    user: User = Depends(get_current_user),
):
    await ScheduleService().delete_schedule_by_id(schedule_id)


async def schedule_update(
    applet_id: int,
    schedule_id: int,
    user: User = Depends(get_current_user),
    schema: EventRequest = Body(...),
) -> Response[PublicEvent]:
    schedule = await ScheduleService().update_schedule(
        applet_id, schedule_id, schema
    )
    return Response(result=PublicEvent(**schedule.dict()))


async def schedule_count(
    applet_id: int,
    user: User = Depends(get_current_user),
) -> Response[PublicEventCount]:

    count: PublicEventCount = await ScheduleService().count_schedules(
        applet_id
    )
    return Response(result=count)
