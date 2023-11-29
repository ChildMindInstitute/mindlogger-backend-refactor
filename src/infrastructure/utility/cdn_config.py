from pydantic import BaseSettings


class CdnConfig(BaseSettings):
    endpoint_url: str | None = None
    region: str | None
    bucket: str | None
    secret_key: str | None
    access_key: str | None
    domain: str = ""
    ttl_signed_urls: int = 3600
