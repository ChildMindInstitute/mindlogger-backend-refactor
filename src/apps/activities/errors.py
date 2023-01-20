from apps.shared.errors import BadRequestError


class ReusableItemChoiceAlreadyExist(BadRequestError):
    def __init__(
        self, *_, message="Reusable item choice already exist"
    ) -> None:
        super().__init__(message=message)
