from pydantic.types import PositiveInt

from apps.users.db.schemas import UserCreateSchema


class User(UserCreateSchema):
    id: PositiveInt

    def __str__(self) -> str:
        return self.username


class UserInDB(User):
    hashed_password: str
