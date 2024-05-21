from datetime import datetime, timezone

from pydantic import Field

from apps.applets.domain.base import Encryption
from apps.shared.domain import PublicModel


class AppletGeneration(PublicModel):
    anchor_date_time: datetime = Field(
        description="Anchor date time",
        default=datetime.now(timezone.utc).replace(
            hour=12
        ),  # make sure tests works in any hour, because it fails when it near midnight in UTC
    )
    encryption: Encryption


image_url = "https://d38b044pevnwc9.cloudfront.net/cutout-nuxt/enhancer/2.jpg"  # noqa: E501
