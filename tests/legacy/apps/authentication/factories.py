from polyfactory.factories.pydantic_factory import ModelFactory

from apps.authentication.domain.logout import UserLogoutRequest

__all__ = [
    "UserLogoutRequestFactory",
]


class UserLogoutRequestFactory(ModelFactory):
    __model__ = UserLogoutRequest
