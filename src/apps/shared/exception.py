from collections import defaultdict
from enum import Enum

from fastapi import Depends
from starlette import status

from apps.shared.enums import Language
from infrastructure.http import get_language


class ExceptionTypes(str, Enum):
    UNDEFINED = "UNDEFINED"
    BAD_REQUEST = 'BAD_REQUEST'
    INVALID_VALUE = 'INVALID_VALUE'
    ACCESS_DENIED = 'ACCESS_DENIED'
    NOT_FOUND = 'NOT_FOUND'


class BaseError(Exception):
    messages = {
        Language.ENGLISH: "Oops, something went wrong."
    }
    fallback_language = Language.ENGLISH

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    type = ExceptionTypes.UNDEFINED

    def __init__(self, language: str = Depends(get_language), **kwargs):
        self.message = self._get_message(
            Language(language)
        ).format(**kwargs)
        super().__init__(self.message)

    def _get_message(self, language: Language) -> str:
        message = self.messages.get(language, None)
        if not message:
            message = self.messages.get(self.fallback_language)
        return message


class ValidationError(BaseError):
    messages = {
        Language.ENGLISH: "Bad request."
    }
    status_code = status.HTTP_400_BAD_REQUEST
    type = ExceptionTypes.BAD_REQUEST


class FieldError(BaseError):
    messages = {
        Language.ENGLISH: "Invalid value."
    }
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    type = ExceptionTypes.INVALID_VALUE
    zero_path = 'body'

    def __init__(self, path=None, **kwargs):
        if path is None:
            path = []
        if self.zero_path:
            path.insert(0, self.zero_path)
        self.path = path
        super().__init__(**kwargs)


class AccessDeniedError(BaseError):
    messages = {
        Language.ENGLISH: "Access denied."
    }
    status_code = status.HTTP_403_FORBIDDEN
    type = ExceptionTypes.ACCESS_DENIED


class NotFoundError(BaseError):
    messages = {
        Language.ENGLISH: "Not found."
    }
    status_code = status.HTTP_404_NOT_FOUND
    type = ExceptionTypes.NOT_FOUND


class InternalServerError(BaseError):
    pass
