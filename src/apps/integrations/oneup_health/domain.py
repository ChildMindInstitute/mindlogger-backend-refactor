import uuid

from pydantic import Field

from apps.shared.domain import PublicModel


class OneupHealthToken(PublicModel):
    access_token: str = Field(default=...)
    refresh_token: str | None = Field(default=None)
    app_user_id: str
    oneup_user_id: int


class RefreshTokenRequest(PublicModel):
    refresh_token: str = Field(description="The refresh token to use for getting a new access token")
    oneup_user_id: int | None = Field(default=0, description="The 1UpHealth user ID (optional)")
    submit_id: uuid.UUID | None = Field(default=None)
    activity_id: uuid.UUID | None = Field(default=None)
