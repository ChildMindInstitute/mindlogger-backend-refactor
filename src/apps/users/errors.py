from apps.shared.enums import Language
from apps.shared.errors import (
    BaseError,
)
from apps.shared.exception import ValidationError, NotFoundError


class UserNotFound(NotFoundError):
    messages = {
        Language.ENGLISH: "User not found"
    }


class UserAlreadyExistError(ValidationError):
    messages = {Language.ENGLISH: "User already exist."}


class EmailAddressError(ValidationError):
    messages = {
        Language.ENGLISH: "Email address is not verified. The following "
                          "identities failed the check: {email}"
    }


class PasswordRecoveryKeyNotFound(NotFoundError):
    messages = {
        Language.ENGLISH: "Password recovery key not found"
    }


class UserIsDeletedError(NotFoundError):
    messages = {
        Language.ENGLISH: "User is deleted"
    }


class UserDeviceNotFound(NotFoundError):
    messages = {
        Language.ENGLISH: "User device is not found"
    }


class UsersError(BaseError):
    def __init__(self, *_, message="Users error") -> None:
        super().__init__(message=message)
