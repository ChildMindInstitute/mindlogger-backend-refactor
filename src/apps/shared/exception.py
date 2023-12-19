from enum import Enum
from gettext import gettext as _

from starlette import status

from apps.shared.enums import Language


class ExceptionTypes(str, Enum):
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
        if self.message_is_template:
            final_message = self.message.format(**kwargs)
        elif args:
            final_message = args[0]
        else:
            final_message = self.message

        super().__init__(final_message, *args[1:])

    @property
    def error(self):
        return _(self.message).format(**self.kwargs)


class ValidationError(BaseError):
    message = _("Bad request.")
    status_code = status.HTTP_400_BAD_REQUEST
    type = ExceptionTypes.BAD_REQUEST


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


class InternalServerError(BaseError):
    pass


class EncryptionError(Exception):
    pass
