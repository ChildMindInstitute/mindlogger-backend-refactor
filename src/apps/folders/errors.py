from apps.shared.errors import AccessDeniedError, ValidationError

__all__ = [
    "FolderAlreadyExist",
    "FolderDoesNotExist",
    "FolderIsNotEmpty",
    "FolderAccessDenied",
    "AppletNotInFolder",
]


class FolderAlreadyExist(ValidationError):
    def __init__(self, *_, message="Folder already exists.") -> None:
        super().__init__(message=message)


class FolderDoesNotExist(ValidationError):
    def __init__(self, *_, message="Folder does not exist.") -> None:
        super().__init__(message=message)


class FolderIsNotEmpty(ValidationError):
    def __init__(
        self,
        *_,
        message="Folder has applets, move applets from folder to delete it.",
    ) -> None:
        super().__init__(message=message)


class FolderAccessDenied(AccessDeniedError):
    def __init__(self, *_, message="Access denied.") -> None:
        super().__init__(message=message)


class AppletNotInFolder(ValidationError):
    def __init__(self, *_, message="Applet not in folder.") -> None:
        super().__init__(message=message)
