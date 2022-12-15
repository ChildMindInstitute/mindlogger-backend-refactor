from apps.shared.errors import BaseError, NotFoundError, ValidationError


class UsersError(BaseError):
    pass


class UserNotFound(NotFoundError):
    pass


class UserIsDeletedError(ValidationError):
    pass
