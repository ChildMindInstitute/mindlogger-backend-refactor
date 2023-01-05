from pydantic import BaseConfig, BaseModel, Extra

__all__ = ["InternalModel", "PublicModel", "CamelCaseModel"]


def to_camelcase(string: str) -> str:
    resp = "".join(word.capitalize() for word in string.split("_"))
    return resp


class CamelCaseModel(BaseModel):
    class Config(BaseConfig):
        alias_generator = to_camelcase


class InternalModel(BaseModel):
    class Config:
        extra = Extra.forbid
        orm_mode = True
        use_enum_values = True
        allow_population_by_field_name = True
        validate_assignment = True


class PublicModel(CamelCaseModel):
    class Config:
        extra = Extra.ignore
        orm_mode = True
        use_enum_values = True
        allow_population_by_field_name = True
        validate_assignment = True
