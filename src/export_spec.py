import json
from typing import Any

import httpx

from infrastructure.app import create_app


def fix_exclusive_values(spec: dict[str, Any]):
    """FastApi generates broken openapi specification for version 3.0. By some reasons exclusive values are generated
    in format for version 3.1. So just fix it manually. Can be removed after migration on openapi v3.1
    Difference in versions are described here https://www.openapis.org/blog/2021/02/16/migrating-from-openapi-3-0-to-3-1-0
    See 'Tweak exclusiveMinimum and exclusiveMaximum'
    """
    schemas = spec["components"]["schemas"]
    for schema in schemas.values():
        properties = schema.get("properties", {})
        for prop in properties.values():
            exclusive_minimum = prop.get("exclusiveMinimum")
            exclusive_maximum = prop.get("exclusiveMaximum")
            if exclusive_minimum is not None:
                prop["minimum"] = exclusive_minimum
                prop["exclusiveMinimum"] = True
            if exclusive_maximum is not None:
                prop["maximum"] = exclusive_maximum
                prop["exclusiveMaximum"] = True
    paths = spec["paths"]
    for path in paths.values():
        for method in path.values():
            for parameter in method.get("parameters", []):
                schema = parameter.get("schema", {})
                exclusive_minimum = schema.get("exclusiveMinimum")
                exclusive_maximum = schema.get("exclusiveMaximum")
                if exclusive_minimum is not None:
                    schema["minimum"] = exclusive_minimum
                    schema["exclusiveMinimum"] = True
                if exclusive_maximum is not None:
                    schema["maximum"] = exclusive_maximum
                    schema["exclusiveMaximum"] = True


def save_to_file(spec: dict[str, Any], file_name: str):
    with open(f"/tmp/{file_name}", "w") as f:
        json.dump(spec, f, indent=4)


def main():
    current_specification_url = "https://api-dev.cmiml.net/openapi.json"
    new_spec = create_app().openapi()
    current_spec = httpx.get(current_specification_url).json()
    fix_exclusive_values(new_spec)
    fix_exclusive_values(current_spec)
    save_to_file(new_spec, "new_spec.json")
    save_to_file(current_spec, "current_spec.json")


if __name__ == "__main__":
    main()
