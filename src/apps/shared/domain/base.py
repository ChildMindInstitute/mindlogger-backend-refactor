from enum import Enum as _Enum

from pydantic import BaseModel, Extra

__all__ = ["InternalModel", "PublicModel", "Enum"]


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


class Enum(_Enum):
    @classmethod
    def values(cls):
        return [element.value for element in cls]
