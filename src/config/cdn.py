from pydantic import BaseModel


class CDNSettings(BaseModel):
    """Configure cdn settings"""

    legacy_prefix: str | None = "mindlogger-legacy/answer"

    region: str | None = None
    # Media Bucket
    bucket: str | None = None
    # Answer Bucket
    bucket_answer: str | None = None
    # Operations Bucket
    bucket_operations: str | None = None
    secret_key: str | None = None
    access_key: str | None = None

    # DR settings
    bucket_override: str | None = None
    bucket_answer_override: str | None = None
    bucket_operations_override: str | None = None

    domain: str = ""
    ttl_signed_urls: int = 3600

    gcp_endpoint_url: str = "https://storage.googleapis.com"
    endpoint_url: str | None = None
    storage_address: str | None = None
    max_concurrent_tasks: int = 10

    @property
    def url(self):
        if self.domain:
            return f"https://{self.domain}/{{key}}"
        return f"{self.storage_address}/{self.bucket}/{{key}}"
