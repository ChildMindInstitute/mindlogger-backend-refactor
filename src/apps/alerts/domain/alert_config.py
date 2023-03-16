import uuid

from pydantic import Field

from apps.shared.domain import PublicModel

__all__ = [
    "AlertsConfigCreateRequest",
    "AlertsConfigCreateResponse",
]


class AlertsConfigCreateRequest(PublicModel):
    """This model represents the request for configuration
    alerts for specific applet and activity item
    """

    applet_id: uuid.UUID = Field(
        description="This field represents the specific applet id"
    )
    activity_item_id: uuid.UUID = Field(
        description="This field represents the specific activity item "
        "id in applet"
    )
    alert_message: str = Field(
        description="This field represents the alert message "
        "which will be shown"
    )
    specific_answer: str = Field(
        description="This field represents the specific answer "
        "upon selection of which an alert will be created"
    )
    viewed: bool = Field(
        description="This is a boolean field that represents "
        "whether the alerts will be shown to the user",
        default=True,
    )


class AlertsConfigCreateResponse(AlertsConfigCreateRequest):
    """This model represents the response for configuration
    alerts for specific applet and activity item
    """

    id: uuid.UUID = Field(
        description="This field represents the id "
        "for specific alert configuration"
    )
