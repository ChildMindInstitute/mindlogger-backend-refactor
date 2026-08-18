import datetime

from pydantic import BaseModel, field_validator


class AccessTokenSettings(BaseModel):
    secret_key: str
    # Set in minutes
    expiration: int = 30
    # Shorter lifetime (minutes) for web/admin clients. None = same as `expiration`.
    # See AuthenticationService.token_expiration_minutes.
    web_admin_expiration: int | None = 15

    @field_validator("secret_key")
    @classmethod
    def check_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Please specify AUTHENTICATION__ACCESS_TOKEN__SECRET_KEY variable")
        return v


class RefreshTokenSettings(BaseModel):
    secret_key: str
    # Set in minutes
    expiration: int = 540
    # Shorter lifetime (minutes) for web/admin clients. None = same as `expiration`.
    # See AuthenticationService.token_expiration_minutes.
    web_admin_expiration: int | None = 30
    # Grace period (seconds) after a web/admin refresh token is rotated during which
    # the old token still redeems for the same replacement pair (absorbs tab races /
    # dropped responses). After it, presenting the old token is treated as reuse.
    rotation_grace_seconds: int = 60

    transition_key: str | None = None
    transition_expire_date: datetime.date | None = None

    @field_validator("secret_key")
    @classmethod
    def check_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Please specify AUTHENTICATION__REFRESH_TOKEN__SECRET_KEY variable")
        return v


class PasswordRecoverSettings(BaseModel):
    # Set in seconds
    expiration: int = 900


class MFATokenSettings(BaseModel):
    """Settings for temporary MFA verification tokens."""

    secret_key: str
    # Set in minutes (matches Redis session TTL)
    expiration: int = 5

    @field_validator("secret_key")
    @classmethod
    def check_secret_key(cls, v: str) -> str:
        if not v:
            raise ValueError("Please specify AUTHENTICATION__MFA_TOKEN__SECRET_KEY variable")
        return v


class AuthenticationSettings(BaseModel):
    access_token: AccessTokenSettings
    refresh_token: RefreshTokenSettings
    algorithm: str = "HS256"
    token_type: str = "Bearer"
    password_recover: PasswordRecoverSettings = PasswordRecoverSettings()
    mfa_token: MFATokenSettings
