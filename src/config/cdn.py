from pydantic import BaseModel, model_validator
from typing_extensions import Self


class CDNSettings(BaseModel):
    """Configure cdn settings"""

    legacy_prefix: str | None = "mindlogger-legacy/answer"

    region: str | None = None

    ## Regular buckets.  Do not change these in DR.  Use the override settings below
    # Media Bucket
    bucket: str | None = None
    # Answer Bucket
    bucket_answer: str | None = None
    # Operations Bucket
    bucket_operations: str | None = None
    secret_key: str | None = None
    access_key: str | None = None

    # KMS
    bucket_kms_enabled: bool = False
    bucket_kms_key_id: str | None = None

    bucket_answer_kms_enabled: bool = False
    bucket_answer_kms_key_id: str | None = None

    bucket_operation_kms_enabled: bool = False
    bucket_operation_kms_key_id: str | None = None

    ## DR settings
    # Override the media bucket name for the DR site
    bucket_override: str | None = None
    # Override the answer bucket name for the DR site
    bucket_answer_override: str | None = None
    # Override the operations bucket name for the DR site
    bucket_operation_override: str | None = None

    # Public domain to front storage keys without scheme for the media bucket
    # In prod this is: media.gettingcurious.com
    domain: str = ""
    ttl_signed_urls: int = 3600

    gcp_endpoint_url: str = "https://storage.googleapis.com"

    # Custom Object store endpoint URL
    # Usually this is a custom S3 endpoint or GCP, etc.
    # Locally for minio type stores it is in the form http://localhost:9000
    endpoint_url: str | None = None

    # If using Minio or some other storage this is used.  Do not set domain
    # This needs to have the URL scheme on it as well (eg http://.....)
    # Effectively this is: Endpoint URL + media bucket name
    storage_address: str | None = None

    max_concurrent_tasks: int = 10

    @model_validator(mode="after")
    def validate_settings(self) -> Self:
        """Validate that domain or endpoint is set.  Cannot be both"""
        if self.domain and (self.endpoint_url or self.storage_address):
            raise ValueError("Either domain or endpoint_url must be set, not both.")

        if self.bucket_kms_enabled and not self.bucket_kms_key_id:
            raise ValueError("bucket_kms_key_id must be set if bucket_kms_enabled is True")

        if self.bucket_answer_kms_enabled and not self.bucket_answer_kms_key_id:
            raise ValueError("bucket_answer_kms_key_id must be set if bucket_answer_kms_enabled is True")

        if self.bucket_operation_kms_enabled and not self.bucket_operation_kms_key_id:
            raise ValueError("bucket_operation_kms_key_id must be set if bucket_operation_kms_enabled is True")

        return self

    @property
    def url(self):
        raise RuntimeError("Use StorageClient.get_public_url instead")
        if self.domain:
            return f"https://{self.domain}/{{key}}"
        return f"{self.storage_address}/{self.bucket}/{{key}}"
