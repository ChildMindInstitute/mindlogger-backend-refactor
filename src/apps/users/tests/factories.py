from pydantic_factories import ModelFactory

from apps.users.domain import (
    PublicUser,
    User,
    UserCreateRequest,
    UserLoginRequest,
    UserUpdateRequest,
)

__all__ = [
    "PublicUserFactory",
    "UserFactory",
    "UserCreateRequestFactory",
    "UserLoginRequestFactory",
    "UserUpdateRequestFactory",
]


class PublicUserFactory(ModelFactory):
    __model__ = PublicUser


class UserFactory(ModelFactory):
    __model__ = User


class UserCreateRequestFactory(ModelFactory):
    __model__ = UserCreateRequest


class UserLoginRequestFactory(ModelFactory):
    __model__ = UserLoginRequest


class UserUpdateRequestFactory(ModelFactory):
    __model__ = UserUpdateRequest
