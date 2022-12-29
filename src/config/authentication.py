from pydantic import BaseModel


class SecretKeysSettings(BaseModel):
    authentication: str = (
        "e51bcf5f4cb8550ff3f6a8bb4dfe112a3da2cf5142929e1b281cd974c88fa66c"
    )
    refresh: str = (
        "5da342d54ed5659f123cdd1cefe439c5aaf7e317a0aba1405375c07d32e097cc"
    )


class TokensExpireSettings(BaseModel):
    # expire_minutes
    access_token: int = 30
    refresh_token: int = 540


class AuthenticationSettings(BaseModel):
    secret_keys: SecretKeysSettings = SecretKeysSettings()
    expire_minutes: TokensExpireSettings = TokensExpireSettings()
    algorithm: str = "HS256"
    token_type: str = "Bearer"
