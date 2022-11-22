from pydantic.types import PositiveInt

from apps.shared.domain import BaseError
from apps.users.db.schemas import UserCreate

USERS_NAMESPACE = "users"


class UsersError(BaseError):
    def __init__(self, message: str | None = None, *args, **kwargs) -> None:
        message = (
            message
            or "Can not find your user in the database. Please register first."
        )
        super().__init__(message, *args, **kwargs)


class User(UserCreate):
    id: PositiveInt

    def __str__(self) -> str:
        return self.username


class UserInDB(User):
    hashed_password: str
