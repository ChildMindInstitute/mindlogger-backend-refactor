from fastapi.routing import APIRouter
from starlette import status

from apps.activities.api.activities import (
    activity_retrieve,
    applet_activities,
    applet_activities_and_flows,
    applet_activities_for_respondent_subject,
    applet_activities_for_subject,
    applet_activities_for_target_subject,
    public_activity_retrieve,
)
from apps.activities.api.reusable_item_choices import item_choice_create, item_choice_delete, item_choice_retrieve
from apps.activities.domain.activity import (
    ActivityOrFlowWithAssignmentsPublic,
    ActivitySingleLanguageWithItemsDetailPublic,
)
from apps.activities.domain.reusable_item_choices import PublicReusableItemChoice
from apps.applets.domain.applet import (
    ActivitiesAndFlowsWithAssignmentDetailsPublic,
    AppletActivitiesAndFlowsDetailsPublic,
    AppletActivitiesDetailsPublic,
)
from apps.shared.domain import Response, ResponseMulti
from apps.shared.domain.response import AUTHENTICATION_ERROR_RESPONSES, DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/activities", tags=["Activities"])
public_router = APIRouter(prefix="/public/activities", tags=["Activities"])

router.post(
    "/item_choices",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[PublicReusableItemChoice],
    responses={
        status.HTTP_201_CREATED: {"model": Response[PublicReusableItemChoice]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(item_choice_create)

router.get(
    "/item_choices",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicReusableItemChoice],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicReusableItemChoice]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(item_choice_retrieve)

router.delete(
    "/item_choices/{id_}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(item_choice_delete)

router.get(
    "/{activity_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[ActivitySingleLanguageWithItemsDetailPublic]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(activity_retrieve)

public_router.get(
    "/{id_}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[ActivitySingleLanguageWithItemsDetailPublic]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(public_activity_retrieve)

router.get(
    "/applet/{applet_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[AppletActivitiesDetailsPublic]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(applet_activities)

router.get(
    "/flows/applet/{applet_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[AppletActivitiesAndFlowsDetailsPublic]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(applet_activities_and_flows)

router.get(
    "/applet/{applet_id}/subject/{subject_id}",
    description="""Get all assigned activities and activity flows for a specific subject.
                """,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[ActivitiesAndFlowsWithAssignmentDetailsPublic]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(applet_activities_for_subject)

router.get(
    "/applet/{applet_id}/target/{subject_id}",
    description="""Get all assigned activities and activity flows for a target subject.
                """,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[ActivityOrFlowWithAssignmentsPublic]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(applet_activities_for_target_subject)

router.get(
    "/applet/{applet_id}/respondent/{subject_id}",
    description="""Get all assigned activities and activity flows for a respondent subject.
                """,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[ActivityOrFlowWithAssignmentsPublic]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(applet_activities_for_respondent_subject)
