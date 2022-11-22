from os import getenv

from pydantic import BaseModel


class AuthenticationSettings(BaseModel):

    secret_key: str = getenv(
        "SECRET_KEY",
        default="e51bcf5f4cb8550ff3f6a8bb4dfe112a"
        "3da2cf5142929e1b281cd974c88fa66c",
    )
    algorithm: str = getenv(
        "ALGORITHM",
        default="HS256",
    )
    access_token_expire_minutes: int = getenv(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        default=30,
    )
