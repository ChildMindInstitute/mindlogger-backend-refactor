from fastapi.routing import APIRouter
from starlette import status

from apps.folders.api import (
    folder_create,
    folder_delete,
    folder_list,
    folder_pin,
    folder_unpin,
    folder_update_name,
)
from apps.folders.domain import FolderPublic
from apps.shared.domain import Response, ResponseMulti
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
)

router = APIRouter(prefix="/folders", tags=["Folders"])

router.get(
    "",
    response_model=ResponseMulti[FolderPublic],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[FolderPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(folder_list)

router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[FolderPublic],
    responses={
        status.HTTP_201_CREATED: {"model": Response[FolderPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(folder_create)

router.put(
    "/{id_}",
    status_code=status.HTTP_200_OK,
    response_model=Response[FolderPublic],
    responses={
        status.HTTP_200_OK: {"model": Response[FolderPublic]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(folder_update_name)

router.delete(
    "/{id_}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={
        **NO_CONTENT_ERROR_RESPONSES,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(folder_delete)


router.post(
    "/{id_}/pin/{applet_id}",
    status_code=status.HTTP_200_OK,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(folder_pin)

router.delete(
    "/{id_}/pin/{applet_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(folder_unpin)
