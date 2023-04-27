from pydantic import BaseModel


class CDNSettings(BaseModel):
    """Configure cdn settings"""

    secret_key: str | None
    access_key: str | None
    region: str | None
    bucket: str | None

    @property
    def url(self):
        return f"https://{self.bucket}.s3.amazonaws.com/{{key}}"
