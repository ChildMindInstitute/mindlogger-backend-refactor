from gettext import gettext as _

from starlette import status

from apps.shared.exception import AccessDeniedError, BaseError, ValidationError


class BadCredentials(ValidationError):
    message = _("Old password is incorrect.")


class InvalidRefreshToken(ValidationError):
    message = _("Invalid refresh token.")


class WeakPassword(ValidationError):
    message = _("Weak password.")


class AuthenticationError(BaseError):
    message = _("Could not validate credentials.")
    status_code = status.HTTP_401_UNAUTHORIZED


class PermissionsError(AccessDeniedError):
    message = _("Not enough permissions.")


class EmailDoesNotExist(AccessDeniedError):
    message = _("That email is not associated with a Curious account.")


class InvalidCredentials(AccessDeniedError):
    message = _("Incorrect email or password")
    status_code = status.HTTP_401_UNAUTHORIZED


class MFATokenInvalidError(AuthenticationError):
    message = _("MFA token is invalid or expired")
    status_code = status.HTTP_401_UNAUTHORIZED


class MFATokenExpiredError(AuthenticationError):
    message = _("MFA token has expired. Please log in again.")
    status_code = status.HTTP_401_UNAUTHORIZED


class MFATokenMalformedError(AuthenticationError):
    message = _("MFA token is malformed or invalid.")
    status_code = status.HTTP_401_UNAUTHORIZED


class MFASessionNotFoundError(AuthenticationError):
    message = _("MFA session not found or expired")
    status_code = status.HTTP_401_UNAUTHORIZED


class InvalidTOTPCodeError(AuthenticationError):
    message = _("Invalid TOTP code")
    status_code = status.HTTP_401_UNAUTHORIZED


class TooManyTOTPAttemptsError(AuthenticationError):
    message = _("Too many invalid TOTP attempts. Please login again.")
    status_code = status.HTTP_429_TOO_MANY_REQUESTS


class MFAGlobalLockoutError(AuthenticationError):
    message = _("Account temporarily locked due to multiple failed MFA attempts. Please try again later.")
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
