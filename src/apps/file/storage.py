import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.workspaces.constants import StorageType
from apps.workspaces.service import workspace
from config import CDNSettings, settings
from infrastructure.utility.cdn_arbitrary import (
    ArbitaryAzureCdnClient,
    ArbitaryGCPCdnClient,
    ArbitaryS3CdnClient,
)
from infrastructure.utility.cdn_client import CDNClient, LogCDN


async def select_storage(
    applet_id: uuid.UUID,
    session: AsyncSession,
):
    service = workspace.WorkspaceService(session, uuid.uuid4())
    info = await service.get_arbitrary_info(applet_id)
    if not info:
        settings_cdn = CDNSettings(
            region=settings.cdn.region,
            bucket=settings.cdn.bucket_answer,
            ttl_signed_urls=settings.cdn.ttl_signed_urls,
            access_key=settings.cdn.access_key,
            secret_key=settings.cdn.secret_key,
        )
        return CDNClient(settings_cdn, env=settings.env)

    bucket_type = info.storage_type.lower()
    arbitary_cdn_settings = CDNSettings(
        region=info.storage_region,
        bucket=info.storage_bucket,
        ttl_signed_urls=settings.cdn.ttl_signed_urls,
        access_key=info.storage_access_key,
        secret_key=info.storage_secret_key,
    )
    match bucket_type:
        case StorageType.AZURE:
            return ArbitaryAzureCdnClient(
                sec_key=info.storage_secret_key,
                bucket=str(info.storage_bucket),
            )
        case StorageType.GCP:
            return ArbitaryGCPCdnClient(
                arbitary_cdn_settings,
                endpoint_url=settings.cdn.gcp_endpoint_url,
                env=settings.env,
            )
        case _:
            # default is aws (logic from legacy app)
            return ArbitaryS3CdnClient(arbitary_cdn_settings, env=settings.env)


def logs_storage():
    settings_cdn = CDNSettings(
        region=settings.cdn.region,
        bucket_answer=settings.cdn.bucket_answer,
        ttl_signed_urls=settings.cdn.ttl_signed_urls,
    )
    return LogCDN(settings_cdn, env=settings.env)
