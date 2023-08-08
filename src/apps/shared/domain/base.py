from typing import TypeVar

from pydantic import BaseModel, Extra

__all__ = [
    "InternalModel",
    "PublicModel",
    "to_camelcase",
    "list_items_to_camel_case",
    "dict_keys_to_camel_case",
    "model_as_camel_case",
]

_BaseModel = TypeVar("_BaseModel", bound=BaseModel)


def to_camelcase(payload: str) -> str:
    if "_" not in payload:
        return payload

    return "".join(
        word.capitalize() if index else word
        for index, word in enumerate(payload.split("_"))
    )


def convert_value_to_camel_case(value):
    if isinstance(value, dict):
        return convert_dict_to_camel_case(value)
    elif isinstance(value, list):
        return [convert_value_to_camel_case(item) for item in value]
    else:
        return value


def convert_dict_to_camel_case(input_dict):
    camel_case_dict = {}
    for key, value in input_dict.items():
        camel_case_key = to_camelcase(key)
        camel_case_dict[camel_case_key] = convert_value_to_camel_case(value)
    return camel_case_dict


def model_as_camel_case(model: _BaseModel) -> _BaseModel:
    """Returns the model but with field names and nested
    keys converted to camel case.
    """
    model_dict = model.dict()
    camel_case_dict = convert_dict_to_camel_case(model_dict)
    return model.__class__(**camel_case_dict)


def dict_keys_to_camel_case(items):
    res = dict()
    for key, value in items.items():
        new_key = to_camelcase(key)
        if isinstance(value, dict):
            res[new_key] = dict_keys_to_camel_case(value)
        elif isinstance(value, list):
            res.update({new_key: list_items_to_camel_case(value)})
        else:
            res[new_key] = value
    return res


def list_items_to_camel_case(items):
    res = []
    for item in items:
        if isinstance(item, dict):
            res.append(list_items_to_camel_case(item))
        elif isinstance(item, list):
            res.append(list_items_to_camel_case(item))
        elif isinstance(item, str):
            res.append(to_camelcase(item))
        else:
            res.append(item)
    return res


class InternalModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = Extra.forbid
        orm_mode = True
        use_enum_values = True
        allow_population_by_field_name = True
        validate_assignment = True
        alias_generator = to_camelcase


class PublicModel(BaseModel):
    class Config:
        arbitrary_types_allowed = True
        extra = Extra.ignore
        orm_mode = True
        use_enum_values = True
        allow_population_by_field_name = True
        validate_assignment = True
        alias_generator = to_camelcase
