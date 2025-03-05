from fastapi.routing import APIRouter
from starlette import status

from apps.schedule.api.schedule import (
    public_schedule_get_all,
    schedule_count,
    schedule_create,
    schedule_create_individual,
    schedule_delete_all,
    schedule_delete_by_id,
    schedule_delete_by_user,
    schedule_get_all,
    schedule_get_all_by_respondent_user,
    schedule_get_all_by_user,
    schedule_get_by_id,
    schedule_get_by_user,
    schedule_import,
    schedule_remove_individual_calendar,
    schedule_retrieve_applet_all_device_events_history,
    schedule_retrieve_applet_all_events_history,
    schedule_update,
)
from apps.schedule.domain.schedule.public import (
    ExportDeviceHistoryDto,
    ExportEventHistoryDto,
    PublicEvent,
    PublicEventByUser,
    PublicEventCount,
)
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
    Response,
    ResponseMulti,
)

router = APIRouter(prefix="/applets", tags=["Applets"])
public_router = APIRouter(prefix="/public/applets", tags=["Applets"])


# Import events
router.post(
    "/{applet_id}/events/import",
    response_model=ResponseMulti[PublicEvent],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": ResponseMulti[PublicEvent]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_import)

# Create individual schedule
router.post(
    "/{applet_id}/events/individual/{respondent_id}",
    response_model=ResponseMulti[PublicEvent],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": ResponseMulti[PublicEvent]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_create_individual)

# Create schedule
router.post(
    "/{applet_id}/events",
    response_model=Response[PublicEvent],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[PublicEvent]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_create)

# Get all schedules
router.get(
    "/{applet_id}/events",
    response_model=ResponseMulti[PublicEvent],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicEvent]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_get_all)

public_router.get(
    "/{key}/events",
    response_model=Response[PublicEventByUser],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicEventByUser]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(public_schedule_get_all)

# Get schedule count
router.get(
    "/{applet_id}/events/count",
    response_model=Response[PublicEventCount],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicEventCount]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_count)

# Delete all schedules by user
router.delete(
    "/{applet_id}/events/delete_individual/{respondent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_delete_by_user)

# Remove individual calendar
router.delete(
    "/{applet_id}/events/remove_individual/{respondent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_remove_individual_calendar)

router.get(
    "/{applet_id}/events/history",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[ExportEventHistoryDto]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(schedule_retrieve_applet_all_events_history)

router.get(
    "/{applet_id}/events/device_history",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[ExportDeviceHistoryDto]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(schedule_retrieve_applet_all_device_events_history)

# Get schedule by id
router.get(
    "/{applet_id}/events/{schedule_id}",
    response_model=Response[PublicEvent],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicEvent]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_get_by_id)

# Delete all schedules
router.delete(
    "/{applet_id}/events",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_delete_all)

# Delete schedule by id
router.delete(
    "/{applet_id}/events/{schedule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_delete_by_id)

# Update schedule
router.put(
    "/{applet_id}/events/{schedule_id}",
    response_model=Response[PublicEvent],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicEvent]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_update)

# Add route to User router
user_router = APIRouter(prefix="/users", tags=["Users"])
# Get schedule by user
user_router.get(
    "/me/events",
    response_model=ResponseMulti[PublicEventByUser],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicEventByUser]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_get_all_by_user)

user_router.get(
    "/me/events/{applet_id}",
    response_model=Response[PublicEventByUser],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicEventByUser]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_get_by_user)

user_router.get(
    "/me/respondent/current_events",
    response_model=ResponseMulti[PublicEventByUser],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicEventByUser]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(schedule_get_all_by_respondent_user)
