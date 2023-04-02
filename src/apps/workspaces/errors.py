from apps.shared.errors import AccessDeniedError, BaseError, NotFoundError

__all__ = [
    "UserAppletAccessesNotFound",
    "AppletAccessDenied",
    "WorkspaceDoesNotExistError",
]


class UserAppletAccessesNotFound(BaseError):
    def __init__(self, *_, id_: int) -> None:
        super().__init__(message=f"No such UserAppletAccess with id={id_}.")


class AppletAccessDenied(AccessDeniedError):
    def __init__(self, *_, message="Access denied to applet.") -> None:
        super().__init__(message=message)


class WorkspaceDoesNotExistError(NotFoundError):
    def __init__(self, *_, message="Workspace does not exist.") -> None:
        super().__init__(message=message)
