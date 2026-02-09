from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageConfig(BaseSettings):
    endpoint_url: str | None = None
    region: str | None = None
    bucket: str | None = None
    secret_key: str | None = None
    access_key: str | None = None
    domain: str = ""
    ttl_signed_urls: int = 3600

    # DR Settings
    bucket_override: str | None = None

    model_config = SettingsConfigDict(extra="ignore")
