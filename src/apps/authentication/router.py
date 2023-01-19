from fastapi.routing import APIRouter
from starlette import status

from apps.authentication.api.auth import (
    delete_access_token,
    get_token,
    refresh_access_token,
)
from apps.authentication.domain.token.public import Login, Token
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
    Response,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Get token
router.post(
    "/login",
    response_model=Response[Login],
    responses={
        status.HTTP_200_OK: {"model": Response[Login]},
        **NO_CONTENT_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(get_token)

# Add token to the blacklist
router.post(
    "/token/delete",
    response_model=Response[Token],
    responses={
        status.HTTP_204_NO_CONTENT: {},
        **AUTHENTICATION_ERROR_RESPONSES,
        **NO_CONTENT_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(delete_access_token)

# Refresh access token
router.post(
    "/token/refresh",
    response_model=Response[Token],
    responses={
        status.HTTP_200_OK: {"model": Response[Token]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **NO_CONTENT_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(refresh_access_token)
