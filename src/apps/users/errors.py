from apps.shared.domain import BaseError


class UsersError(BaseError):
    pass


class UserNotFound(BaseError):
    pass
