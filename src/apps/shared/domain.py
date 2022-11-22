from pydantic import BaseModel, Extra


class BaseError(Exception):
    def __init__(self, message: str | None = None, *args, **kwargs) -> None:
        message = message or "Adding error"
        super().__init__(message, *args, **kwargs)


class Model(BaseModel):
    class Config:
        extra = Extra.ignore
        orm_mode = True
        use_enum_values = True
        allow_population_by_field_name = True
        validate_assignment = True
