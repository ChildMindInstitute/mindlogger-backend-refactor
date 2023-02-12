from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.schedule.domain.schedule.public import PublicEvent, PublicEventCount
from apps.schedule.domain.schedule.requests import EventRequest
from apps.schedule.service.schedule import ScheduleService
from apps.shared.domain import Response, ResponseMulti
from apps.users.domain import User


# TODO: Add logic to allow to create applets by permissions
# TODO: Restrict by admin
async def schedule_create(
    applet_id: int,
    schema: EventRequest = Body(...),
    user: User = Depends(get_current_user),
) -> Response[PublicEvent]:
    """Create a new event for an applet."""

    schedule = await ScheduleService().create_schedule(schema, applet_id)
    return Response(result=PublicEvent(**schedule.dict()))


# TODO: Add logic to allow to create applets by permissions
# TODO: Restrict by admin
async def schedule_get_by_id(
    applet_id: int,
    schedule_id: int,
    user: User = Depends(get_current_user),
) -> Response[PublicEvent]:
    """Get a schedule by id."""
    schedule = await ScheduleService().get_schedule_by_id(schedule_id)
    return Response(result=PublicEvent(**schedule.dict()))


# TODO: Add logic to allow to create applets by permissions
# TODO: Restrict by admin
async def schedule_get_all(
    applet_id: int,
    user: User = Depends(get_current_user),
) -> ResponseMulti[PublicEvent]:
    """Get all schedules for an applet."""
    schedules = await ScheduleService().get_all_schedules(applet_id)

    return ResponseMulti(result=schedules)


# TODO: Add logic to allow to create applets by permissions
# TODO: Restrict by admin
async def schedule_delete_all(
    applet_id: int,
    user: User = Depends(get_current_user),
):
    """Delete all schedules for an applet."""
    await ScheduleService().delete_all_schedules(applet_id)


# TODO: Add logic to allow to create applets by permissions
# TODO: Restrict by admin
async def schedule_delete_by_id(
    applet_id: int,
    schedule_id: int,
    user: User = Depends(get_current_user),
):
    """Delete a schedule by id."""
    await ScheduleService().delete_schedule_by_id(schedule_id)


# TODO: Add logic to allow to create applets by permissions
# TODO: Restrict by admin
async def schedule_update(
    applet_id: int,
    schedule_id: int,
    user: User = Depends(get_current_user),
    schema: EventRequest = Body(...),
) -> Response[PublicEvent]:
    """Update a schedule by id."""
    schedule = await ScheduleService().update_schedule(
        applet_id, schedule_id, schema
    )
    return Response(result=PublicEvent(**schedule.dict()))


# TODO: Add logic to allow to create applets by permissions
# TODO: Restrict by admin
async def schedule_count(
    applet_id: int,
    user: User = Depends(get_current_user),
) -> Response[PublicEventCount]:
    """Get the count of schedules for an applet."""
    count: PublicEventCount = await ScheduleService().count_schedules(
        applet_id
    )
    return Response(result=count)


# TODO: Add logic to allow to create applets by permissions
# TODO: Restrict by admin
async def schedule_delete_by_user(
    applet_id: int,
    user_id: int,
    user: User = Depends(get_current_user),
):
    """Delete all schedules for a user."""
    await ScheduleService().delete_by_user_id(
        applet_id=applet_id, user_id=user_id
    )
