from apps.shared.errors import NotFoundError


class FileNotFoundError(NotFoundError):
    def __init__(self, message: str = "File not found") -> None:
        super().__init__(message=message)
