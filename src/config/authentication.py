import datetime

from pydantic import field_validator
from pydantic_settings import BaseSettings


class AccessTokenSettings(BaseSettings):
    secret_key: str
    # Set in minutes
    expiration: int = 30

    @field_validator("secret_key")
    @classmethod
    def check_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Please specify AUTHENTICATION__ACCESS_TOKEN__SECRET_KEY variable")
        return v


class RefreshTokenSettings(BaseSettings):
    secret_key: str
    # Set in minutes
    expiration: int = 540

    transition_key: str | None = None
    transition_expire_date: datetime.date | None = None

    @field_validator("secret_key")
    @classmethod
    def check_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Please specify AUTHENTICATION__REFRESH_TOKEN__SECRET_KEY variable")
        return v


class PasswordRecoverSettings(BaseSettings):
    # Set in seconds
    expiration: int = 900


class MFATokenSettings(BaseSettings):
    """Settings for temporary MFA verification tokens."""

    secret_key: str = Field("", env="AUTHENTICATION__MFA_TOKEN__SECRET_KEY")
    # Set in minutes (matches Redis session TTL)
    expiration: int = 5

    @validator("secret_key")
    def check_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Please specify AUTHENTICATION__MFA_TOKEN__SECRET_KEY variable")
        return v


class AuthenticationSettings(BaseSettings):
    access_token: AccessTokenSettings
    refresh_token: RefreshTokenSettings
    algorithm: str = "HS256"
    token_type: str = "Bearer"
    password_recover: PasswordRecoverSettings = PasswordRecoverSettings()
    mfa_token: MFATokenSettings
