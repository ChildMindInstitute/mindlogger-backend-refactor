from gettext import gettext as _

from apps.shared.exception import AccessDeniedError, NotFoundError

__all__ = [
    "UserAppletAccessesNotFound",
    "AppletAccessDenied",
    "WorkspaceDoesNotExistError",
    "UserAppletAccessesDenied",
]


class WorkspaceDoesNotExistError(NotFoundError):
    message = _("Workspace does not exist.")


class UserAppletAccessesDenied(AccessDeniedError):
    message = _("Access denied.")


class AppletAccessDenied(AccessDeniedError):
    message = _("Access denied to applet.")


class WorkspaceAccessDenied(AccessDeniedError):
    message = _("Access denied to workspace.")


class UserAppletAccessesNotFound(NotFoundError):
    message = _("No such UserAppletAccess with id={id_}.")
