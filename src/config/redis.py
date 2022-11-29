import typing

from pydantic import BaseModel


class RedisSettings(BaseModel):
    """Configure redis settings"""

    host: str = ""
    port: str = ""
    db: str = ""
    expire_duration: typing.Optional[int]
