from gettext import gettext as _

from starlette import status

from apps.authentication.constants import AuthErrorCode
from apps.shared.exception import AccessDeniedError, BaseError, ValidationError


class BadCredentials(ValidationError):
    message = _("Old password is incorrect.")


class InvalidRefreshToken(ValidationError):
    message = _("Invalid refresh token.")
    error_code = AuthErrorCode.INVALID_REFRESH_TOKEN


class WeakPassword(ValidationError):
    message = _("Weak password.")


class AuthenticationError(BaseError):
    message = _("Could not validate credentials.")
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = AuthErrorCode.AUTHENTICATION_ERROR


class PermissionsError(AccessDeniedError):
    message = _("Not enough permissions.")
    error_code = AuthErrorCode.PERMISSIONS_ERROR


class EmailDoesNotExist(AccessDeniedError):
    message = _("That email is not associated with a Curious account.")
    error_code = AuthErrorCode.EMAIL_DOES_NOT_EXIST


class InvalidCredentials(AccessDeniedError):
    message = _("Incorrect email or password")
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = AuthErrorCode.INVALID_CREDENTIALS


class MFATokenInvalidError(AuthenticationError):
    message = _("MFA token is invalid or expired")
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = AuthErrorCode.MFA_TOKEN_INVALID


class MFATokenExpiredError(AuthenticationError):
    message = _("MFA token has expired. Please log in again.")
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = AuthErrorCode.MFA_TOKEN_EXPIRED


class MFATokenMalformedError(AuthenticationError):
    message = _("MFA token is malformed or invalid.")
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = AuthErrorCode.MFA_TOKEN_MALFORMED


class MFASessionNotFoundError(AuthenticationError):
    message = _("MFA session not found or expired")
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = AuthErrorCode.MFA_SESSION_NOT_FOUND


class InvalidTOTPCodeError(AuthenticationError):
    message = _("Invalid TOTP code")
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = AuthErrorCode.MFA_INVALID_TOTP_CODE

    def __init__(
        self,
        session_attempts_remaining: int | None = None,
        global_attempts_remaining: int | None = None,
        **kwargs,
    ):
        metadata: dict[str, int] = {}
        if session_attempts_remaining is not None:
            metadata["session_attempts_remaining"] = session_attempts_remaining
        if global_attempts_remaining is not None:
            metadata["global_attempts_remaining"] = global_attempts_remaining
        super().__init__(metadata=metadata if metadata else None, **kwargs)


class TooManyTOTPAttemptsError(AuthenticationError):
    message = _("Too many invalid TOTP attempts. Please login again.")
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = AuthErrorCode.MFA_TOO_MANY_ATTEMPTS

    def __init__(
        self,
        session_attempts_remaining: int | None = None,
        global_attempts_remaining: int | None = None,
        lockout_reason: str | None = None,
        **kwargs,
    ):
        metadata: dict[str, int | str] = {}
        if session_attempts_remaining is not None:
            metadata["session_attempts_remaining"] = session_attempts_remaining
        if global_attempts_remaining is not None:
            metadata["global_attempts_remaining"] = global_attempts_remaining
        if lockout_reason:
            metadata["lockout_reason"] = lockout_reason
        super().__init__(metadata=metadata if metadata else None, **kwargs)


class MFAGlobalLockoutError(AuthenticationError):
    message = _("Account temporarily locked due to multiple failed MFA attempts. Please try again later.")
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = AuthErrorCode.MFA_GLOBAL_LOCKOUT

    def __init__(
        self,
        global_attempts_remaining: int = 0,
        **kwargs,
    ):
        metadata: dict[str, int] = {
            "global_attempts_remaining": global_attempts_remaining,
        }
        super().__init__(metadata=metadata, **kwargs)
