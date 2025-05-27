import uuid
from typing import Union

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from apps.file.storage import select_storage
from config import settings
from infrastructure.database.deps import get_session
from infrastructure.utility.cdn_arbitrary import ArbitraryAzureCdnClient, ArbitraryGCPCdnClient, ArbitraryS3CdnClient
from infrastructure.utility.cdn_client import CDNClient
from infrastructure.utility.cdn_config import CdnConfig


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

# TODO Pycharm says this isn't used
async def get_answer_bucket(
    applet_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
) -> Union[
    CDNClient,
    ArbitraryAzureCdnClient,
    ArbitraryGCPCdnClient,
    ArbitraryS3CdnClient,
]:
    return await select_storage(applet_id=applet_id, session=session)


async def get_legacy_bucket():
    """@deprecated: use get_answer_bucket instead."""
    config_cdn = CdnConfig(
        region=settings.cdn.legacy_region,
        bucket=settings.cdn.legacy_bucket,
        access_key=settings.cdn.legacy_access_key,
        secret_key=settings.cdn.legacy_secret_key,
        ttl_signed_urls=settings.cdn.ttl_signed_urls,
    )
    return CDNClient(config_cdn, env=settings.env)
