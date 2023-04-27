import uuid

from apps.shared.enums import Language
from apps.shared.errors import BaseError
from apps.shared.exception import NotFoundError, AccessDeniedError

__all__ = [
    "UserAppletAccessesNotFound",
    "AppletAccessDenied",
    "WorkspaceDoesNotExistError",
    "UserAppletAccessesDenied",
]


class WorkspaceDoesNotExistError(NotFoundError):
    messages = {
        Language.ENGLISH: "Workspace does not exist."
    }


class UserAppletAccessesDenied(AccessDeniedError):
    messages = {
        Language.ENGLISH: "Access denied."
    }


class AppletAccessDenied(AccessDeniedError):
    messages = {
        Language.ENGLISH: "Access denied to applet."
    }


class WorkspaceAccessDenied(AccessDeniedError):
    messages = {
        Language.ENGLISH: "Access denied to workspace."
    }


class UserAppletAccessesNotFound(BaseError):
    def __init__(self, *_, id_: uuid.UUID) -> None:
        super().__init__(message=f"No such UserAppletAccess with id={id_}.")
