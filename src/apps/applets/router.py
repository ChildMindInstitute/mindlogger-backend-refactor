from fastapi.routing import APIRouter
from starlette import status

from apps.applets.api.applets import (
    activity_report_config_update,
    applet_conceal,
    applet_delete,
    applet_duplicate,
    applet_encryption_update,
    applet_link_create,
    applet_link_delete,
    applet_link_get,
    applet_list,
    applet_publish,
    applet_retrieve,
    applet_retrieve_base_info,
    applet_retrieve_base_info_by_key,
    applet_retrieve_by_key,
    applet_set_data_retention,
    applet_set_folder,
    applet_set_report_configuration,
    applet_unique_name_get,
    applet_update,
    applet_version_changes_retrieve,
    applet_version_retrieve,
    applet_versions_retrieve,
    flow_report_config_update, flow_item_history,
)
from apps.applets.domain import AppletUniqueName, PublicAppletHistoryChange, PublicHistory
from apps.applets.domain.applet import (
    AppletActivitiesBaseInfo,
    AppletRetrieveResponse,
    AppletSingleLanguageDetailForPublic,
    AppletSingleLanguageDetailPublic,
    AppletSingleLanguageInfoPublic,
)
from apps.applets.domain.applet_link import AppletLink
from apps.applets.domain.applets import public_detail, public_history_detail
from apps.shared.domain import Response, ResponseMulti
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
)

router = APIRouter(prefix="/applets", tags=["Applets"])
public_router = APIRouter(prefix="/public/applets", tags=["Applets"])

router.get(
    "",
    response_model=ResponseMulti[AppletSingleLanguageInfoPublic],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[AppletSingleLanguageInfoPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_list)

router.get(
    "/{applet_id}",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": AppletRetrieveResponse[AppletSingleLanguageDetailPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_retrieve)

router.get(
    "/{applet_id}/versions",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicHistory],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicHistory]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_versions_retrieve)

router.get(
    "/{applet_id}/versions/{version}",
    status_code=status.HTTP_200_OK,
    response_model=Response[public_history_detail.AppletDetailHistory],
    responses={
        status.HTTP_200_OK: {"model": Response[public_history_detail.AppletDetailHistory]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_version_retrieve)

router.get(
    "/{applet_id}/versions/{version}/changes",
    status_code=status.HTTP_200_OK,
    response_model=Response[PublicAppletHistoryChange],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicAppletHistoryChange]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_version_changes_retrieve)

router.post(
    "/{applet_id}/duplicate",
    description="""Duplicate an existing applet, and optionally its report server configuration""",
    response_model_by_alias=True,
    response_model=Response[public_detail.Applet],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[public_detail.Applet]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_duplicate)

router.post(
    "/{applet_id}/report_configuration",
    description="""This endpoint to set report configuration""",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_set_report_configuration)

router.post(
    "/{applet_id}/publish",
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_publish)

router.post(
    "/{applet_id}/conceal",
    response_model_by_alias=True,
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_conceal)

router.post(
    "/set_folder",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_set_folder)

router.post(
    "/unique_name",
    status_code=status.HTTP_200_OK,
    response_model=Response[AppletUniqueName],
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_unique_name_get)

router.put(
    "/{applet_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[public_detail.Applet],
    responses={
        status.HTTP_200_OK: {"model": Response[public_detail.Applet]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_update)

router.post(
    "/{applet_id}/encryption",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[public_detail.Encryption]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_encryption_update)

router.delete(
    "/{applet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(applet_delete)

router.post(
    "/{applet_id}/access_link",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[AppletLink],
    responses={
        status.HTTP_201_CREATED: {"model": Response[AppletLink]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_link_create)

router.get(
    "/{applet_id}/access_link",
    status_code=status.HTTP_200_OK,
    response_model=Response[AppletLink],
    responses={
        status.HTTP_200_OK: {"model": Response[AppletLink]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_link_get)

router.delete(
    "/{applet_id}/access_link",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(applet_link_delete)

router.post(
    "/{applet_id}/retentions",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_set_data_retention)


router.put(
    "/{applet_id}/activities/{activity_id}/report_configuration",
    status_code=status.HTTP_200_OK,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(activity_report_config_update)


router.put(
    "/{applet_id}/flows/{flow_id}/report_configuration",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(flow_report_config_update)


router.get(
    "/{applet_id}/flows/item_history",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(flow_item_history)

router.get(
    "/{applet_id}/base_info",
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": AppletActivitiesBaseInfo},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_retrieve_base_info)

public_router.get(
    "/{key}",
    status_code=status.HTTP_200_OK,
    response_model=Response[AppletSingleLanguageDetailForPublic],
    responses={
        status.HTTP_200_OK: {"model": Response[AppletSingleLanguageDetailForPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_retrieve_by_key)

public_router.get(
    "/{key}/base_info",
    status_code=status.HTTP_200_OK,
    response_model=Response[AppletActivitiesBaseInfo],
    responses={
        status.HTTP_200_OK: {"model": Response[AppletActivitiesBaseInfo]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_retrieve_base_info_by_key)
