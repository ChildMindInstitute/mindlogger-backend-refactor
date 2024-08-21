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
    bucket_operations: str | None
    secret_key: str | None
    access_key: str | None

    domain: str = ""
    ttl_signed_urls: int = 3600

    gcp_endpoint_url = "https://storage.googleapis.com"
    endpoint_url: str | None = None
    storage_address: str | None = None
    max_concurrent_tasks: int = 10

    @property
    def url(self):
        if self.domain:
            return f"https://{self.domain}/{{key}}"
        return f"{self.storage_address}/{self.bucket}/{{key}}"
