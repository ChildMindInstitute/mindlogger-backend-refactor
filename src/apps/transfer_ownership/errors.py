from apps.shared.enums import Language
from apps.shared.errors import BaseError, ValidationError
from apps.shared.exception import NotFoundError


class TransferNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "Transfer request not found"
    }


class TransferError(BaseError):
    def __init__(self, message: str = "Transfer service error") -> None:
        super().__init__(message=message)


class TransferAlreadyExist(ValidationError):
    def __init__(
            self, message: str = "Transfer request already exists"
    ) -> None:
        super().__init__(message=message)


class TransferEmailError(ValidationError):
    def __init__(self, *_, message="Transfer email is incorrect") -> None:
        super().__init__(*_, message=message)
