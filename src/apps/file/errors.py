from apps.shared.errors import NotFoundError


class FileNotFoundError(NotFoundError):
    def __init__(self, *args) -> None:
        super().__init__("File not found", *args)
