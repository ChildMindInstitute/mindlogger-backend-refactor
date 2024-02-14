from typing import Literal, Optional

from pydantic import AnyHttpUrl, BaseModel, validator

__all__ = ["CorsSettings"]


class CorsSettings(BaseModel):
    allow_origins: list[AnyHttpUrl | Literal["*"]] = ["*"]
    allow_origin_regex: Optional[str] = None
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]
    allow_credentials: bool = True
    expose_headers: list[str] = []
    max_age: int = 600

    @validator(
        "allow_origins",
        "allow_methods",
        "allow_headers",
        "expose_headers",
        pre=True,
    )
    def as_list(cls, value: str):
        return value.split(",")
