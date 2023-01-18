from apps.shared.errors import NotFoundError, ValidationError


class UsersError(ValidationError):
    pass


class UserNotFound(NotFoundError):
    pass


class UserIsDeletedError(ValidationError):
    pass
