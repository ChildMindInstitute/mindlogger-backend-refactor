from pydantic import BaseModel, Extra


class BaseError(Exception):
    def __init__(self, message="", *args, **kwargs) -> None:
        fallback = "Unhandled error"
        super().__init__(message or fallback, *args, **kwargs)


class InternalModel(BaseModel):
    class Config:
        extra = Extra.forbid
        orm_mode = True
        use_enum_values = True
        allow_population_by_field_name = True
        validate_assignment = True


class PublicModel(BaseModel):
    class Config:
        extra = Extra.ignore
        orm_mode = True
        use_enum_values = True
        allow_population_by_field_name = True
        validate_assignment = True
