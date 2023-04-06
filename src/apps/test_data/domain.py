from datetime import datetime

from pydantic import Field

from apps.shared.domain import PublicModel


class AnchorDateTime(PublicModel):
    anchor_date_time: datetime = Field(
        description="Anchor date time", default=datetime.now()
    )


image_url = "https://d38b044pevnwc9.cloudfront.net/cutout-nuxt/enhancer/2.jpg"  # noqa: E501
