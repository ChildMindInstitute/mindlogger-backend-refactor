from pydantic import BaseModel, Extra

__all__ = [
    "InternalModel",
    "PublicModel",
    "to_camelcase",
    "list_items_to_camel_case",
    "dict_keys_to_camel_case",
]


def to_camelcase(string: str) -> str:
    resp = "".join(
        word.capitalize() if index else word
        for index, word in enumerate(string.split("_"))
    )
    return resp


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
