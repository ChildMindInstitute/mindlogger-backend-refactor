from pydantic_factories import ModelFactory

from apps.users.domain import UserLogoutRequest

__all__ = [
    "UserLogoutRequestFactory",
]


class UserLogoutRequestFactory(ModelFactory):
    __model__ = UserLogoutRequest
