import json
import re
from typing import TypeVar

from pydantic import BaseModel as PBaseModel
from pydantic import Extra

__all__ = [
    "InternalModel",
    "PublicModel",
    "PublicModelNoExtra",
    "to_camelcase",
    "list_items_to_camel_case",
    "dict_keys_to_camel_case",
    "model_as_camel_case",
]

_BaseModel = TypeVar("_BaseModel", bound=PBaseModel)


def to_camelcase(payload: str) -> str:
    if "_" not in payload:
        return payload

    return "".join(word.capitalize() if index else word for index, word in enumerate(payload.split("_")))


def camel_case(match_obj):
    return match_obj.group(1) + match_obj.group(2).upper()


def convert_to_camel(match_obj):
    if match_obj.group() is not None:
        res_str = re.sub(r"(.*?)_([a-zA-Z])", camel_case, match_obj.group())
        return res_str


def convert_str_to_camel_case(input_str: str):
    res_str = re.sub(r'"(\w+)":', convert_to_camel, input_str)
    string_as_dict = json.loads(res_str)
    return string_as_dict


def model_as_camel_case(model: _BaseModel) -> _BaseModel:
    """Returns the model but with field names and nested
    keys converted to camel case.
    """
    model_json = model.json()
    camel_case_dict = convert_str_to_camel_case(model_json)
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


class BaseModel(PBaseModel):
    @classmethod
    def field_alias(cls, field_name: str):
        return cls.__fields__[field_name].alias


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


class PublicModelNoExtra(PublicModel):
    class Config(PublicModel.Config):
        extra = Extra.forbid
