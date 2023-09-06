from pydantic import BaseModel


class CDNSettings(BaseModel):
    """Configure cdn settings"""

    legacy_region: str | None
    legacy_bucket: str | None
    legacy_secret_key: str | None
    legacy_access_key: str | None

    region: str | None
    bucket: str | None
    bucket_answer: str | None
    secret_key: str | None
    access_key: str | None

    domain: str = ""
    ttl_signed_urls: int | None

    @property
    def url(self):
        return f"https://{self.domain}/{{key}}"
