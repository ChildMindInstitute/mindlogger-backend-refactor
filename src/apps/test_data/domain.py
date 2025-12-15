from datetime import datetime, timezone
from typing import Annotated

from pydantic import Field

from apps.applets.domain.base import Encryption
from apps.shared.domain import PublicModel


class AppletGeneration(PublicModel):
    # make sure tests works in any hour, because it fails when it near midnight in UTC
    anchor_date_time: Annotated[
        datetime,
        Field(description="Anchor date time"),
    ] = datetime.now(timezone.utc).replace(hour=12)
    encryption: Encryption


image_url = "https://d38b044pevnwc9.cloudfront.net/cutout-nuxt/enhancer/2.jpg"  # noqa: E501
