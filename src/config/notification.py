from pydantic import BaseModel


class NotificationSettings(BaseModel):
    """Configure FCM notification settings"""

    api_key: str = ""
