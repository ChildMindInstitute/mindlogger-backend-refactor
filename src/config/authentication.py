import datetime

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

    transition_key: str | None = None
    transition_expire_date: datetime.date | None = None

    @validator("secret_key")
    def check_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Please specify AUTHENTICATION__REFRESH_TOKEN__SECRET_KEY variable")
        return v


class PasswordRecoverSettings(BaseSettings):
    # Set in seconds
    expiration: int = 900


class AuthenticationSettings(BaseSettings):
    access_token: AccessTokenSettings
    refresh_token: RefreshTokenSettings
    algorithm: str = "HS256"
    token_type: str = "Bearer"
    password_recover: PasswordRecoverSettings = PasswordRecoverSettings()
