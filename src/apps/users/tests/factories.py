from pydantic_factories import ModelFactory

from apps.users.domain import (
    ChangePasswordRequest,
    UserCreateRequest,
    UserUpdateRequest,
)

__all__ = [
    "UserCreateRequestFactory",
    "UserUpdateRequestFactory",
    "PasswordUpdateRequestFactory",
]


class UserCreateRequestFactory(ModelFactory):
    __model__ = UserCreateRequest


class UserUpdateRequestFactory(ModelFactory):
    __model__ = UserUpdateRequest


class PasswordUpdateRequestFactory(ModelFactory):
    __model__ = ChangePasswordRequest
