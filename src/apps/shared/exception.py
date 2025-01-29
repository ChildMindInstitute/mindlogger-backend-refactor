from enum import StrEnum
from gettext import gettext as _

from starlette import status

from apps.shared.enums import Language


class ExceptionTypes(StrEnum):
    UNDEFINED = "UNDEFINED"
    BAD_REQUEST = "BAD_REQUEST"
    INVALID_VALUE = "INVALID_VALUE"
    ACCESS_DENIED = "ACCESS_DENIED"
    NOT_FOUND = "NOT_FOUND"


class BaseError(Exception):
    message_is_template: bool = False
    message = _("Oops, something went wrong.")
    fallback_language = Language.ENGLISH

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    type = ExceptionTypes.UNDEFINED

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.updated_message = None
        if self.args and not self.message_is_template:
            self.updated_message = args[0]
        super().__init__(self.message.format(**kwargs))

    @property
    def error(self):
        if self.updated_message:
            return self.updated_message
        return _(self.message).format(**self.kwargs)


class ValidationError(BaseError):
    message = _("Bad request.")
    status_code = status.HTTP_400_BAD_REQUEST
    type = ExceptionTypes.BAD_REQUEST
    code: str | None = None


class FieldError(BaseError):
    message = _("Invalid value.")
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    type = ExceptionTypes.INVALID_VALUE
    zero_path: str | None = "body"

    def __init__(self, path=None, **kwargs):
        if path is None:
            path = []
        if self.zero_path:
            path.insert(0, self.zero_path)
        self.path = path
        super().__init__(**kwargs)


class AccessDeniedError(BaseError):
    message = _("Access denied.")
    status_code = status.HTTP_403_FORBIDDEN
    type = ExceptionTypes.ACCESS_DENIED


class NotFoundError(BaseError):
    message = _("Not found.")
    status_code = status.HTTP_404_NOT_FOUND
    type = ExceptionTypes.NOT_FOUND


class UnauthorizedError(BaseError):
    message = _("Unauthorized.")
    status_code = status.HTTP_401_UNAUTHORIZED
    type = ExceptionTypes.ACCESS_DENIED


class InternalServerError(BaseError):
    pass


class EncryptionError(Exception):
    pass
