from fastapi.routing import APIRouter
from starlette import status

from apps.library.api import (
    cart_add,
    cart_get,
    library_check_name,
    library_get_all,
    library_get_by_id,
    library_get_url,
    library_share_applet,
    library_update,
)
from apps.library.domain import (
    AppletLibraryFull,
    AppletLibraryInfo,
    Cart,
    PublicLibraryItem,
)
from apps.shared.domain import Response, ResponseMulti
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
)

router = APIRouter(prefix="/library", tags=["Library"])

router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[AppletLibraryFull],
    responses={
        status.HTTP_201_CREATED: {"model": Response[AppletLibraryFull]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(library_share_applet)

router.post(
    "/check_name",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(library_check_name)

router.get(
    "/cart",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicLibraryItem],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicLibraryItem]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(cart_get)

router.post(
    "/cart",
    status_code=status.HTTP_200_OK,
    response_model=Response[Cart],
    responses={
        status.HTTP_200_OK: {"model": Response[Cart]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(cart_add)


router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicLibraryItem],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicLibraryItem]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
    response_model_by_alias=True,
)(library_get_all)

router.get(
    "/{library_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[PublicLibraryItem],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicLibraryItem]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(library_get_by_id)

router.put(
    "/{library_id}",
    status_code=status.HTTP_200_OK,
    response_model=Response[AppletLibraryFull],
    responses={
        status.HTTP_200_OK: {"model": Response[AppletLibraryFull]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(library_update)


applet_router = APIRouter(prefix="/applets", tags=["Applets"])
applet_router.get(
    "/{applet_id}/library_link",
    status_code=status.HTTP_200_OK,
    response_model=Response[AppletLibraryInfo],
    responses={
        status.HTTP_200_OK: {"model": Response[AppletLibraryInfo]},
        **DEFAULT_OPENAPI_RESPONSE,
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(library_get_url)
