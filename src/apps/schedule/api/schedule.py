import uuid
from copy import deepcopy

from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.schedule.domain.schedule.filters import EventQueryParams
from apps.schedule.domain.schedule.public import (
    PublicEvent,
    PublicEventByUser,
    PublicEventCount,
)
from apps.schedule.domain.schedule.requests import EventRequest
from apps.schedule.service.schedule import ScheduleService
from apps.shared.domain import Response, ResponseMulti
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic, session_manager


# TODO: Add logic to allow to create events by permissions
# TODO: Restrict by admin
async def schedule_create(
    applet_id: uuid.UUID,
    schema: EventRequest = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[PublicEvent]:
    """Create a new event for an applet."""
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_applet_schedule_create_access(applet_id)
        schedule = await ScheduleService(session).create_schedule(
            schema, applet_id
        )
    return Response(result=PublicEvent(**schedule.dict()))


async def schedule_get_by_id(
    applet_id: uuid.UUID,
    schedule_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[PublicEvent]:
    """Get a schedule by id."""
    async with atomic(session):
        schedule = await ScheduleService(session).get_schedule_by_id(
            applet_id=applet_id, schedule_id=schedule_id
        )
    return Response(result=PublicEvent(**schedule.dict()))


async def schedule_get_all(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(EventQueryParams)),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[PublicEvent]:
    """Get schedules for an applet. If respondentId is provided,it
    will return only individual events for that respondent. If respondentId
    is not provided, it will return only general events for the applet."""
    async with atomic(session):
        schedules = await ScheduleService(session).get_all_schedules(
            applet_id, deepcopy(query_params)
        )

    return ResponseMulti(result=schedules, count=len(schedules))


async def public_schedule_get_all(
    key: uuid.UUID,
    session=Depends(session_manager.get_session),
) -> Response[PublicEventByUser]:
    """Get all schedules for an applet."""
    async with atomic(session):
        schedules = await ScheduleService(session).get_public_all_schedules(
            key
        )

    return Response(result=schedules)


async def schedule_delete_all(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    """Delete all schedules for an applet."""
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_applet_schedule_create_access(applet_id)
        await ScheduleService(session).delete_all_schedules(applet_id)


async def schedule_delete_by_id(
    applet_id: uuid.UUID,
    schedule_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    """Delete a schedule by id."""
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_applet_schedule_create_access(applet_id)
        await ScheduleService(session).delete_schedule_by_id(
            schedule_id, applet_id
        )


async def schedule_update(
    applet_id: uuid.UUID,
    schedule_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: EventRequest = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[PublicEvent]:
    """Update a schedule by id."""
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_applet_schedule_create_access(applet_id)
        schedule = await ScheduleService(session).update_schedule(
            applet_id, schedule_id, schema
        )
    return Response(result=PublicEvent(**schedule.dict()))


async def schedule_count(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[PublicEventCount]:
    """Get the count of schedules for an applet."""
    async with atomic(session):
        count: PublicEventCount = await ScheduleService(
            session
        ).count_schedules(applet_id)
    return Response(result=count)


async def schedule_delete_by_user(
    applet_id: uuid.UUID,
    respondent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    """Delete all schedules for a respondent and create default ones."""
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_applet_schedule_create_access(applet_id)
        await ScheduleService(session).delete_by_user_id(
            applet_id=applet_id, user_id=respondent_id
        )


async def schedule_get_all_by_user(
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[PublicEventByUser]:
    """Get all schedules for a user."""
    async with atomic(session):
        schedules = await ScheduleService(session).get_events_by_user(
            user_id=user.id
        )
        count = await ScheduleService(session).count_events_by_user(
            user_id=user.id
        )
    return ResponseMulti(result=schedules, count=count)


async def schedule_get_by_user(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[PublicEventByUser]:
    """Get all schedules for a respondent per applet id."""
    async with atomic(session):
        schedules = await ScheduleService(
            session
        ).get_events_by_user_and_applet(user_id=user.id, applet_id=applet_id)
    return Response(result=schedules)


async def schedule_remove_individual_calendar(
    applet_id: uuid.UUID,
    respondent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    """Remove individual calendar for a respondent."""
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_applet_schedule_create_access(applet_id)
        await ScheduleService(session).remove_individual_calendar(
            applet_id=applet_id, user_id=respondent_id
        )


# TODO: Add logic to allow to create events by permissions
# TODO: Restrict by admin
async def schedule_import(
    applet_id: uuid.UUID,
    schemas: list[EventRequest] = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[PublicEvent]:
    """Create a new event for an applet."""
    async with atomic(session):
        schedules = await ScheduleService(session).import_schedule(
            schemas, applet_id
        )
    return ResponseMulti(
        result=schedules,
        count=len(schedules),
    )
