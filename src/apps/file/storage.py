import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.workspaces.constants import StorageType
from apps.workspaces.service import workspace
from config import CDNSettings, settings
from infrastructure.utility.cdn_arbitrary import CdnClientBlob, CdnClientS3
from infrastructure.utility.cdn_client import CDNClient


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
    match bucket_type:
        case StorageType.AZURE:
            return CdnClientBlob(sec_key=info.storage_secret_key)
        case StorageType.GCP:
            return CdnClientS3(
                region=info.storage_region,
                bucket=info.storage_bucket,
                domain="https://storage.googleapis.com",
                acc_key=info.storage_access_key,
                sec_key=info.storage_secret_key,
            )
        case _:
            # default is aws (logic from legacy app)
            return CdnClientS3(
                region=info.storage_region,
                bucket=info.storage_bucket,
                acc_key=info.storage_access_key,
                sec_key=info.storage_secret_key,
            )
