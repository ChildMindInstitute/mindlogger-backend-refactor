from fastapi.routing import APIRouter
from starlette import status

from apps.shared.domain import Response, ResponseMulti
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
)
from apps.themes.api.themes import (
    create_theme,
    delete_theme_by_id,
    get_themes,
    update_theme_by_id,
)
from apps.themes.domain import PublicTheme

router = APIRouter(prefix="/themes", tags=["Themes"])

router.get(
    "",
    response_model=ResponseMulti[PublicTheme],
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[PublicTheme]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(get_themes)

router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=Response[PublicTheme],
    responses={
        status.HTTP_201_CREATED: {"model": Response[PublicTheme]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(create_theme)

router.delete(
    "/{pk}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={
        **NO_CONTENT_ERROR_RESPONSES,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(delete_theme_by_id)

router.put(
    "/{pk}",
    response_model=Response[PublicTheme],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicTheme]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(update_theme_by_id)
