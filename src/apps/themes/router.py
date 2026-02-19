from fastapi.routing import APIRouter
from starlette import status

from apps.shared.domain import ResponseMulti
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
)
from apps.themes.api.themes import get_themes
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


