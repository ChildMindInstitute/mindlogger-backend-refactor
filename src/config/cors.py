from typing import Annotated, Any, Optional

from pydantic import BaseModel, field_validator
from pydantic_settings import NoDecode

__all__ = ["CorsSettings"]


class CorsSettings(BaseModel):
    # Annotated[*, NoDecode] to avoid parsing environment variable as JSON
    allow_origins: Annotated[list[str], NoDecode] = ["*"]
    allow_origin_regex: Optional[str] = None
    allow_methods: Annotated[list[str], NoDecode] = ["*"]
    allow_headers: Annotated[list[str], NoDecode] = ["*"]
    allow_credentials: bool = True
    expose_headers: Annotated[list[str], NoDecode] = []
    max_age: int = 600

    @field_validator("allow_origins", "allow_methods", "allow_headers", "expose_headers", mode="before")
    @classmethod
    def as_list(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.split(",")
        return value
