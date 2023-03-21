from fastapi.routing import APIRouter
from starlette import status

from apps.applets.api.applets import (
    applet_create,
    applet_delete,
    applet_link_create,
    applet_link_delete,
    applet_link_get,
    applet_list,
    applet_retrieve,
    applet_set_data_retention,
    applet_set_folder,
    applet_unique_name_get,
    applet_update,
    applet_version_changes_retrieve,
    applet_version_retrieve,
    applet_versions_retrieve,
    applet_users_list,
)
from apps.applets.domain import (
    AppletUniqueName,
    PublicAppletHistoryChange,
    PublicHistory,
)
from apps.applets.domain.applet import AppletDetailPublic, AppletInfoPublic
from apps.applets.domain.applet_link import AppletLink
from apps.applets.domain.applets import public_detail, public_history_detail
from apps.shared.domain import Response, ResponseMulti
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
)
from apps.workspaces.domain.user_applet_access import PublicAppletUser

router = APIRouter(prefix="/applets", tags=["Applets"])

router.get(
    "",
    response_model=ResponseMulti[AppletInfoPublic],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[AppletInfoPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_list)

router.get(
    "/{id_}",
    status_code=status.HTTP_200_OK,
    response_model=Response[AppletDetailPublic],
    responses={
        status.HTTP_200_OK: {"model": Response[AppletDetailPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_retrieve)

router.get(
    "/{id_}/users",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicAppletUser],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicAppletUser]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_users_list)

router.get(
    "/{id_}/versions",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicHistory],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicHistory]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_versions_retrieve)

router.get(
    "/{id_}/versions/{version}",
    status_code=status.HTTP_200_OK,
    response_model=Response[public_history_detail.AppletDetailHistory],
    responses={
        status.HTTP_200_OK: {
            "model": Response[public_history_detail.AppletDetailHistory]
        },
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_version_retrieve)

router.get(
    "/{id_}/versions/{version}/changes",
    status_code=status.HTTP_200_OK,
    response_model=Response[PublicAppletHistoryChange],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicAppletHistoryChange]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_version_changes_retrieve)

router.post(
    "",
    response_model=Response[public_detail.Applet],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[public_detail.Applet]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_create)

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
    "/{id_}",
    status_code=status.HTTP_200_OK,
    response_model=Response[public_detail.Applet],
    responses={
        status.HTTP_200_OK: {"model": Response[public_detail.Applet]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_update)

router.delete(
    "/{id_}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(applet_delete)

router.post(
    "/{id_}/access_link",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[AppletLink],
    responses={
        status.HTTP_201_CREATED: {"model": Response[AppletLink]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_link_create)

router.get(
    "/{id_}/access_link",
    status_code=status.HTTP_200_OK,
    response_model=Response[AppletLink],
    responses={
        status.HTTP_200_OK: {"model": Response[AppletLink]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_link_get)

router.delete(
    "/{id_}/access_link",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(applet_link_delete)

router.post(
    "/{id_}/retentions",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(applet_set_data_retention)
