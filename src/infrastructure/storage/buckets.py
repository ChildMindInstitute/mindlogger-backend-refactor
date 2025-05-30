from config import settings
from infrastructure.storage.cdn_client import CDNClient
from infrastructure.storage.cdn_config import CdnConfig


async def get_media_bucket() -> CDNClient:
    config = CdnConfig(
        endpoint_url=settings.cdn.endpoint_url,
        region=settings.cdn.region,
        bucket=settings.cdn.bucket,
        secret_key=settings.cdn.secret_key,
        access_key=settings.cdn.access_key,
        domain=settings.cdn.domain,
        ttl_signed_urls=settings.cdn.ttl_signed_urls,
    )
    return CDNClient(config, env=settings.env)


async def get_operations_bucket() -> CDNClient:
    config = CdnConfig(
        endpoint_url=settings.cdn.endpoint_url,
        region=settings.cdn.region,
        bucket=settings.cdn.bucket_operations,
        secret_key=settings.cdn.secret_key,
        access_key=settings.cdn.access_key,
        domain=settings.cdn.domain,
        ttl_signed_urls=settings.cdn.ttl_signed_urls,
    )
    return CDNClient(config, env=settings.env)


async def get_log_bucket() -> CDNClient:
    config = CdnConfig(
        endpoint_url=settings.cdn.endpoint_url,
        access_key=settings.cdn.access_key,
        secret_key=settings.cdn.secret_key,
        region=settings.cdn.region,
        bucket=settings.cdn.bucket_answer,
        ttl_signed_urls=settings.cdn.ttl_signed_urls,
    )
    return CDNClient(config, env=settings.env)
