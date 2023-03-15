from datetime import datetime

from pydantic import Field

from apps.shared.domain import PublicModel


class AnchorDateTime(PublicModel):
    anchor_date_time: datetime | None = Field(
        ..., description="Anchor date time"
    )
