from pydantic import BaseModel, Extra

__all__ = ["InternalModel", "PublicModel"]


def to_camelcase(string: str) -> str:
    resp = "".join(
        word.capitalize() if index else word
        for index, word in enumerate(string.split("_"))
    )
    return resp


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
        alias_generator = to_camelcase
