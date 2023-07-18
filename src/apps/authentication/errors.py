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
