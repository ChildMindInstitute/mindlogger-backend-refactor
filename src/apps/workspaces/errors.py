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


class WorkspaceFolderManipulationAccessDenied(AccessDeniedError):
    message = _("Access denied to manipulate workspace folders.")


class UserAppletAccessesNotFound(NotFoundError):
    message = _("No such UserAppletAccess with id={id_}.")


class UserAppletAccessNotFound(NotFoundError):
    message = _("Not access related to user and applet found.")


class RemoveOwnPermissionAccessDenied(AccessDeniedError):
    message = _("Access denied to remove own permission.")


class AppletEncryptionUpdateDenied(AccessDeniedError):
    message = _("Access denied to update encryption.")


class AppletCreationAccessDenied(AccessDeniedError):
    message = _("Access denied to create applet in current workspace.")


class AppletEditionAccessDenied(AccessDeniedError):
    message = _("Access denied to edit applet in current workspace.")


class AppletDuplicateAccessDenied(AccessDeniedError):
    message = _("Access denied to duplicate applet in current workspace.")


class AppletDeleteAccessDenied(AccessDeniedError):
    message = _("Access denied to delete applet in current workspace.")


class AnswerCreateAccessDenied(AccessDeniedError):
    message = _("Access denied to submit answer to applet.")


class AnswerViewAccessDenied(AccessDeniedError):
    message = _("Access denied to view applet answers.")


class AnswerNoteCRUDAccessDenied(AccessDeniedError):
    message = _("Access denied to manipulate with notes of answers.")


class AppletInviteAccessDenied(AccessDeniedError):
    message = _("Access denied to manipulate with invites of the applet.")


class AppletSetScheduleAccessDenied(AccessDeniedError):
    message = _(
        "Access denied to manipulate with "
        "schedules and notifications of the applet."
    )


class TransferOwnershipAccessDenied(AccessDeniedError):
    message = _(
        "Access denied to create transfer ownership request for the applet."
    )


class PublishConcealAccessDenied(AccessDeniedError):
    message = _("Access denied to publish/conceal the applet.")


class AccessDeniedToUpdateOwnAccesses(AccessDeniedError):
    message = _("Access denied to update own accesses in current workspace.")
