from fastapi.routing import APIRouter
from starlette import status

from apps.authentication.domain.recovery_code.public import RecoveryCodesListResponse
from apps.shared.domain import Response
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
)
from apps.subjects.api import get_my_subject
from apps.subjects.domain import SubjectReadResponse
from apps.users.api import (
    password_recovery,
    password_recovery_approve,
    password_recovery_healthcheck,
    password_update,
    user_create,
    user_delete,
    user_download_recovery_codes,
    user_get_recovery_codes,
    user_mfa_totp_disable_initiate,
    user_mfa_totp_initiate,
    user_mfa_totp_verify,
    user_retrieve,
    user_save_device,
    user_update,
)
from apps.users.domain import MFADisableInitiateResponse, PublicUser, TOTPInitiateResponse, TOTPVerifyResponse, UserDevice

router = APIRouter(prefix="/users", tags=["Users"])

# User create
router.post(
    "",
    response_model=Response[PublicUser],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[PublicUser]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_create)

# User retrieve
router.get(
    "/me",
    response_model=Response[PublicUser],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicUser]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_retrieve)

# User update
router.put(
    "/me",
    response_model=Response[PublicUser],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicUser]},
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_update)

# User delete
router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_delete)

# Password update
router.put(
    "/me/password",
    response_model=Response[PublicUser],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicUser]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(password_update)

# Password recovery
router.post(
    "/me/password/recover",
    status_code=status.HTTP_201_CREATED,
    responses={
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(password_recovery)

# Password recovery approve
router.post(
    "/me/password/recover/approve",
    response_model=Response[PublicUser],
    responses={
        status.HTTP_200_OK: {"model": Response[PublicUser]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **NO_CONTENT_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(password_recovery_approve)

# Password recovery healthcheck
router.get(
    "/me/password/recover/healthcheck",
)(password_recovery_healthcheck)

router.get(
    "/me/subjects/{applet_id}",
    response_model=Response[SubjectReadResponse],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[SubjectReadResponse]},
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(get_my_subject)

router.post(
    "/me/devices",
    response_model=Response[UserDevice],
    responses={
        status.HTTP_200_OK: {"model": Response[UserDevice]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_save_device)

# TOTP initiate
router.post(
    "/me/mfa/totp/initiate",
    response_model=Response[TOTPInitiateResponse],
    name="user_mfa_totp_initiate",
    responses={
        status.HTTP_200_OK: {"model": Response[TOTPInitiateResponse]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_mfa_totp_initiate)

# TOTP verify
router.post(
    "/me/mfa/totp/verify",
    response_model=Response[TOTPVerifyResponse],
    name="user_mfa_totp_verify",
    summary="Verify TOTP and enable MFA",
    description=(
        "Verifies TOTP code and enables MFA. Returns 10 recovery codes on first-time setup (displayed once only)."
    ),
    responses={
        status.HTTP_200_OK: {"model": Response[TOTPVerifyResponse]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_mfa_totp_verify)

# TOTP disable initiate
router.post(
    "/me/mfa/totp/disable/initiate",
    response_model=Response[MFADisableInitiateResponse],
    name="user_mfa_totp_disable_initiate",
    summary="Initiate MFA disable flow",
    description=(
        "Initiates the MFA disable process by creating a verification session. "
        "Returns an mfa_token that must be used to verify identity before disabling MFA."
    ),
    responses={
        status.HTTP_200_OK: {"model": Response[MFADisableInitiateResponse]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_mfa_totp_disable_initiate)

# Get recovery codes
router.get(
    "/me/mfa/recovery-codes",
    response_model=Response[RecoveryCodesListResponse],
    name="user_get_recovery_codes",
    summary="Get recovery codes list",
    description=(
        "Returns all recovery codes with their usage status. "
        "Each code shows whether it has been used and when. Requires MFA to be enabled."
    ),
    responses={
        status.HTTP_200_OK: {"model": Response[RecoveryCodesListResponse]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_get_recovery_codes)

# Download recovery codes
router.get(
    "/me/mfa/recovery-codes/download",
    response_model=None,
    name="user_download_recovery_codes",
    summary="Download recovery codes as text file",
    description=(
        "Downloads all recovery codes with their usage status as a plain text file. Requires MFA to be enabled."
    ),
    responses={
        status.HTTP_200_OK: {
            "description": "Text file download",
            "content": {"text/plain": {"schema": {"type": "string"}}},
        },
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(user_download_recovery_codes)
