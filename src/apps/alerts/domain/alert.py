import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "AlertCreate",
    "Alert",
    "AlertPublic",
]


class _AlertBase(BaseModel):
    """This model used for internal needs
    as a base model for request and response
    """

    respondent_id: uuid.UUID = Field(
        description="This field represents the specific respondent_id"
    )
    alert_config_id: uuid.UUID = Field(
        description="This field represents the specific alert config id"
    )
    applet_id: uuid.UUID = Field(
        description="This field represents the specific applet id"
    )
    activity_item_histories_id_version: str = Field(
        description="This field represents the specific activity item "
        "histories id version in applet"
    )


class AlertCreate(_AlertBase, InternalModel):
    """This model represents the alerts for specific
    activity items answer and specific respondent for save in database
    """

    specific_answer: str = Field(
        description="This field represents the specific answer "
        "upon selection of which an alert will be created"
    )
    alert_message: str = Field(
        description="This field represents the alert message "
        "which will be shown"
    )


class Alert(_AlertBase, InternalModel):
    """This model represents the alert"""

    id: uuid.UUID = Field(
        description="This field represents the id " "for specific alert"
    )
    is_watched: bool = Field(
        description="This field indicates whether this alert has been watched."
    )


class AlertPublic(_AlertBase, PublicModel):
    """This model represents the alert"""

    id: uuid.UUID = Field(
        description="This field represents the id " "for specific alert"
    )
    is_watched: bool = Field(
        description="This field indicates whether this alert has been watched."
    )
    alert_message: str = Field(
        description="This field represents the alert message "
        "which will be shown"
    )
    created_at: datetime = Field(
        description="This field represents when this alert was created"
    )
    applet_name: str = Field(
        description="This field represents the specific applet name"
    )
    meta: dict = Field(
        description="This field represents the meta data for respondent"
        "which which contains the fields - nickname and secret_user_id"
    )
