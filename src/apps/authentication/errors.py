from starlette import status

from apps.shared.enums import Language
from apps.shared.exception import ValidationError, AccessDeniedError, BaseError


class BadCredentials(ValidationError):
    messages = {
        Language.ENGLISH: "Bad credentials"
    }


class WeakPassword(ValidationError):
    messages = {
        Language.ENGLISH: "Weak password."
    }


class AuthenticationError(BaseError):
    messages = {
        Language.ENGLISH: "Could not validate credentials"
    }
    status_code = status.HTTP_401_UNAUTHORIZED


class PermissionsError(AccessDeniedError):
    messages = {
        Language.ENGLISH: "Not enough permissions"
    }
