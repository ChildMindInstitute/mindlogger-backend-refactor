from pydantic import BaseSettings, Field, validator


class AccessTokenSettings(BaseSettings):
    secret_key: str = Field("", env="AUTHENTICATION__ACCESS_TOKEN__SECRET_KEY")
    # Set in minutes
    expiration: int = 30

    @validator("secret_key")
    def check_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Please specify AUTHENTICATION__ACCESS_TOKEN__SECRET_KEY variable")
        return v


class RefreshTokenSettings(BaseSettings):
    secret_key: str = Field("", env="AUTHENTICATION__REFRESH_TOKEN__SECRET_KEY")
    # Set in minutes
    expiration: int = 540

    @validator("secret_key")
    def check_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Please specify AUTHENTICATION__REFRESH_TOKEN__SECRET_KEY variable")
        return v


class PasswordRecoverSettings(BaseSettings):
    # Set in seconds
    expiration: int = 900


class AuthenticationSettings(BaseSettings):
    access_token: AccessTokenSettings = AccessTokenSettings()
    refresh_token: RefreshTokenSettings = RefreshTokenSettings()
    algorithm: str = "HS256"
    token_type: str = "Bearer"
    password_recover: PasswordRecoverSettings = PasswordRecoverSettings()
