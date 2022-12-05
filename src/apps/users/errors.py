from apps.shared.errors import BaseError, NotFoundError


class UsersError(BaseError):
    pass


class UserNotFound(NotFoundError):
    pass
