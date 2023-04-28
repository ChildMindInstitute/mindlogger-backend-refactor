from pydantic import BaseModel


class CDNSettings(BaseModel):
    """Configure cdn settings"""

    region: str | None
    bucket: str | None
    domain: str = ""

    @property
    def url(self):
        return f"https://{self.domain}/{{key}}"
