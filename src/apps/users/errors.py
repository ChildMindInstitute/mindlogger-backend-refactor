from apps.shared.errors import BadRequestError, BaseError, NotFoundError


class UsersError(BaseError):
    def __init__(self, *_, message="Users error") -> None:
        super().__init__(message=message)


class UserNotFound(NotFoundError):
    def __init__(self, *_, message="User not found") -> None:
        super().__init__(message=message)


class UserIsDeletedError(BadRequestError):
    def __init__(self, *_, message="User is deleted") -> None:
        super().__init__(message=message)
