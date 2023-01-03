from pydantic import BaseModel, validator

__all__ = ["CorsSettings"]


class CorsSettings(BaseModel):
    allow_origin_regex: str = r".*"
    allow_credentials: bool = True
    allow_methods: list[str] = ["*"]
    allow_headers: list[str] = ["*"]

    @validator("allow_methods", "allow_headers", pre=True)
    def as_list(cls, value: str):
        return value.split(",")
