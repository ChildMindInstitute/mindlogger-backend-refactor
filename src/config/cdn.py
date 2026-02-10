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
    bucket_answer_override: str | None = None

    # What is the difference between domain and storage_address?
    # In prod this is: media.gettingcurious.com
    domain: str = ""
    ttl_signed_urls: int = 3600

    gcp_endpoint_url: str = "https://storage.googleapis.com"

    # Underlying client (eg boto3) endpoint URL
    endpoint_url: str | None = None

    # This does not seem to be used
    storage_address: str | None = None
    max_concurrent_tasks: int = 10

    # This does not seem useful
    @property
    def url(self):
        raise RuntimeError("Use StorageClient.get_public_url instead")
        if self.domain:
            return f"https://{self.domain}/{{key}}"
        return f"{self.storage_address}/{self.bucket}/{{key}}"
