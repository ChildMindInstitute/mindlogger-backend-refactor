from apps.shared.errors import ValidationError


class AppletDoesNotExist(ValidationError):
    pass


class DoesNotHaveAccess(ValidationError):
    pass
