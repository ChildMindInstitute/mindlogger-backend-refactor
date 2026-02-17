from pydantic_settings import BaseSettings, SettingsConfigDict

from config import CDNSettings


class StorageConfig(BaseSettings):
    """Configuration class for storage service.  Convenience layer between application and object storage."""

    # Custom (S3 or other) endpoint URL
    endpoint_url: str | None = None
    region: str | None = None
    bucket: str | None = None
    secret_key: str | None = None
    access_key: str | None = None

    # Public domain to front storage keys without scheme
    # TODO Default to null??
    domain: str = ""
    # Overrides the storage URL.  Useful for local dev for minio, etc
    # TODO Is this needed for arbitrary server?
    storage_address: str | None = None

    ttl_signed_urls: int = 3600

    # DR Settings
    bucket_override: str | None = None

    model_config = SettingsConfigDict(extra="ignore")

    @classmethod
    def generate_media_settings(cls, cdn_settings: CDNSettings) -> "StorageConfig":
        return cls(
            domain=cdn_settings.domain,
            storage_address=cdn_settings.storage_address,
            bucket=cdn_settings.bucket,
            bucket_override=cdn_settings.bucket_override,
            endpoint_url=cdn_settings.endpoint_url,
            region=cdn_settings.region,
            secret_key=cdn_settings.secret_key,
            access_key=cdn_settings.access_key,
            ttl_signed_urls=cdn_settings.ttl_signed_urls,
        )

    @classmethod
    def generate_answer_settings(cls, cdn_settings: CDNSettings) -> "StorageConfig":
        return cls(
            bucket=cdn_settings.bucket_answer,
            bucket_override=cdn_settings.bucket_answer_override,
            endpoint_url=cdn_settings.endpoint_url,
            region=cdn_settings.region,
            secret_key=cdn_settings.secret_key,
            access_key=cdn_settings.access_key,
            ttl_signed_urls=cdn_settings.ttl_signed_urls,
        )

    @classmethod
    def generate_operations_settings(cls, cdn_settings: CDNSettings) -> "StorageConfig":
        return cls(
            bucket=cdn_settings.bucket_operations,
            bucket_override=cdn_settings.bucket_operation_override,
            endpoint_url=cdn_settings.endpoint_url,
            region=cdn_settings.region,
            secret_key=cdn_settings.secret_key,
            access_key=cdn_settings.access_key,
            ttl_signed_urls=cdn_settings.ttl_signed_urls,
        )

    @classmethod
    def generate_logs_settings(cls, cdn_settings: CDNSettings) -> "StorageConfig":
        return cls(
            bucket=cdn_settings.bucket_answer,
            bucket_override=cdn_settings.bucket_answer_override,
            endpoint_url=cdn_settings.endpoint_url,
            region=cdn_settings.region,
            secret_key=cdn_settings.secret_key,
            access_key=cdn_settings.access_key,
            ttl_signed_urls=cdn_settings.ttl_signed_urls,
        )
