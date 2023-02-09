from apps.shared.errors import ValidationError


class AppletDoesNotExist(ValidationError):
    def __init__(self, *_, message="Applet does not exist.") -> None:
        super().__init__(message=message)


class DoesNotHaveAccess(ValidationError):
    def __init__(self, *_, message="Access denied.") -> None:
        super().__init__(message=message)
