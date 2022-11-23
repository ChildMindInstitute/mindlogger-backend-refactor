from pydantic import BaseModel


class CDNSettings(BaseModel):
    """Configure cdn settings"""

    secret_key: str = ""
    access_key: str = ""
    region: str = ""
    bucket: str = ""
    env: str = ""
