from fastapi.routing import APIRouter
from starlette import status

from apps.authentication.api.auth import (
    delete_access_token,
    delete_refresh_token,
    get_token,
    refresh_access_token,
    verify_mfa_recovery_code,
    verify_mfa_totp,
)
from apps.authentication.deps import openapi_auth
from apps.authentication.domain.login import (
    MFARequiredResponse,
    UserLogin,
)
from apps.authentication.domain.token.public import Token
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
    response_model=Response[UserLogin | MFARequiredResponse],
    responses={
        status.HTTP_200_OK: {"model": Response[UserLogin | MFARequiredResponse]},
        **NO_CONTENT_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(get_token)

# Verify MFA TOTP code
router.post(
    "/mfa/totp/verify",
    response_model=Response[UserLogin],
    responses={
        status.HTTP_200_OK: {"model": Response[UserLogin]},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Too many failed attempts"},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(verify_mfa_totp)

# Verify MFA recovery code
router.post(
    "/mfa/recovery-codes/verify",
    response_model=Response[UserLogin],
    responses={
        status.HTTP_200_OK: {"model": Response[UserLogin]},
        status.HTTP_404_NOT_FOUND: {"description": "No unused recovery codes found"},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Too many failed attempts"},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(verify_mfa_recovery_code)

# Add token to the blacklist
router.post(
    "/logout",
    responses={
        status.HTTP_200_OK: {"model": str},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(delete_access_token)

router.post(
    "/logout2",
    responses={
        status.HTTP_200_OK: {"model": str},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(delete_refresh_token)

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

# Swagger authorizations
router.post(
    "/openapi",
    responses={
        status.HTTP_200_OK: {},
        **NO_CONTENT_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(openapi_auth)
