from pydantic import BaseSettings


class CdnConfig(BaseSettings):
    region: str | None
    bucket: str | None
    secret_key: str | None
    access_key: str | None
    domain: str = ""
    ttl_signed_urls: int = 3600
