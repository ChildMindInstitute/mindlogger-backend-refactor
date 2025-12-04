from polyfactory.factories.pydantic_factory import ModelFactory

from apps.users.domain import (
    ChangePasswordRequest,
    PasswordRecoveryApproveRequest,
    PasswordRecoveryInfo,
    TOTPInitiateResponse,
    TOTPVerifyRequest,
    TOTPVerifyResponse,
    UserCreateRequest,
    UserUpdateRequest,
)
from infrastructure.cache.domain import CacheEntry

__all__ = [
    "UserCreateRequestFactory",
    "UserUpdateRequestFactory",
    "PasswordUpdateRequestFactory",
    "PasswordRecoveryApproveRequestFactory",
    "CacheEntryFactory",
    "PasswordRecoveryInfoFactory",
    "TOTPInitiateResponseFactory",
    "TOTPVerifyRequestFactory",
    "TOTPVerifyResponseFactory",
]


class UserCreateRequestFactory(ModelFactory):
    __model__ = UserCreateRequest


class UserUpdateRequestFactory(ModelFactory):
    __model__ = UserUpdateRequest


class PasswordUpdateRequestFactory(ModelFactory):
    __model__ = ChangePasswordRequest


class PasswordRecoveryApproveRequestFactory(ModelFactory):
    __model__ = PasswordRecoveryApproveRequest


class PasswordRecoveryInfoFactory(ModelFactory):
    __model__ = PasswordRecoveryInfo


class CacheEntryFactory(ModelFactory):
    __model__ = CacheEntry


class TOTPInitiateResponseFactory(ModelFactory):
    __model__ = TOTPInitiateResponse


class TOTPVerifyRequestFactory(ModelFactory):
    __model__ = TOTPVerifyRequest


class TOTPVerifyResponseFactory(ModelFactory):
    __model__ = TOTPVerifyResponse
