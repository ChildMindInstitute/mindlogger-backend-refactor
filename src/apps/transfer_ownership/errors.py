from apps.shared.errors import BaseError, NotFoundError, ValidationError


class TransferError(BaseError):
    def __init__(self, message: str = "Transfer service error") -> None:
        super().__init__(message=message)


class TransferAlreadyExist(ValidationError):
    def __init__(
        self, message: str = "Transfer request already exists"
    ) -> None:
        super().__init__(message=message)


class TransferNotFoundError(NotFoundError):
    def __init__(self, *_, message="Transfer request not found") -> None:
        super().__init__(*_, message=message)
