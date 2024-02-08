from datetime import datetime

from pydantic import Field

from apps.applets.domain.base import Encryption
from apps.shared.domain import PublicModel


class AppletGeneration(PublicModel):
    anchor_date_time: datetime = Field(description="Anchor date time", default=datetime.utcnow())
    encryption: Encryption


image_url = "https://d38b044pevnwc9.cloudfront.net/cutout-nuxt/enhancer/2.jpg"  # noqa: E501
