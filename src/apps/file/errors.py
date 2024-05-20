from gettext import gettext as _

from fastapi import status

from apps.shared.exception import BaseError, ExceptionTypes, NotFoundError


class FileNotFoundError(NotFoundError):
    message = _("File not found.")


class SomethingWentWrongError(BaseError):
    message = _("Something went wrong. Try later.")
    status_code = status.HTTP_400_BAD_REQUEST
    type = ExceptionTypes.BAD_REQUEST
