from pydantic import Field

from apps.shared.domain import PublicModel


class OneupHealthToken(PublicModel):
    access_token: str = Field(default=...)
    refresh_token: str = Field(default=...)
    app_user_id: str
    oneup_user_id: int


class RefreshTokenRequest(PublicModel):
    refresh_token: str = Field(description="The refresh token to use for getting a new access token")


class OneupHealthRefreshToken(PublicModel):
    access_token: str = Field(default=...)
    refresh_token: str = Field(default=...)
