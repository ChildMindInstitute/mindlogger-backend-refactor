from pydantic import BaseModel


class AuthenticationSettings(BaseModel):

    secret_key: str = "e51bcf5f4cb8550ff3f6a8bb4dfe112a3da2cf5142929e1b281cd974c88fa66c"
    refresh_secret_key: str = "5da342d54ed5659f123cdd1cefe439c5aaf7e317a0aba1405375c07d32e097cc"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 540
