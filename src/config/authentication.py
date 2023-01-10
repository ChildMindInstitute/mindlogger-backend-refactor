from pydantic import BaseModel


class AccessTokenSettings(BaseModel):
    secret_key: str = (
        "e51bcf5f4cb8550ff3f6a8bb4dfe112a3da2cf5142929e1b281cd974c88fa66c"
    )
    # Set in minutes
    expiration: int = 30


class RefreshTokenSettings(BaseModel):
    secret_key: str = (
        "5da342d54ed5659f123cdd1cefe439c5aaf7e317a0aba1405375c07d32e097cc"
    )
    # Set in minutes
    expiration: int = 540


class PasswordRecoverSettings(BaseModel):
    # Set in seconds
    expiration: int = 600


class AuthenticationSettings(BaseModel):
    access_token: AccessTokenSettings = AccessTokenSettings()
    refresh_token: RefreshTokenSettings = RefreshTokenSettings()
    algorithm: str = "HS256"
    token_type: str = "Bearer"
    password_recover: PasswordRecoverSettings = PasswordRecoverSettings()
