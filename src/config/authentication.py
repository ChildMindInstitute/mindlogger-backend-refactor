from pydantic import BaseModel


class AuthenticationSettings(BaseModel):

    secret_key: str = (
        "e51bcf5f4cb8550ff3f6a8bb4dfe112a3da2cf5142929e1b281cd974c88fa66c"
    )
    algorithm: str = "HS256"
    token_type: str = "Bearer"
    access_token_expire_minutes: int = 30
