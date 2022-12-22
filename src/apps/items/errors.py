from apps.shared.errors import ValidationError


class ItemTemplateAlreadyExist(ValidationError):
    def __init__(self, *args) -> None:
        message = "Item template already exist"
        super().__init__(message, *args)
