import uuid

from pydantic import Field

from apps.shared.domain import PublicModel


class OneupHealthToken(PublicModel):
    access_token: str = Field(default=...)
    refresh_token: str | None = Field(default=None)
    subject_id: uuid.UUID
    oneup_user_id: int
