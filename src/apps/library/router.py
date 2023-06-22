from fastapi.routing import APIRouter
from starlette import status

from apps.library.api import (
    library_check_name,
    library_get_all,
    library_get_by_id,
    library_share_applet,
)
from apps.library.domain import AppletLibraryFull, PublicLibraryItem
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
    "",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[PublicLibraryItem],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicLibraryItem]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
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
