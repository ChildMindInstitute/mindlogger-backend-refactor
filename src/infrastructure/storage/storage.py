import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.workspaces.constants import StorageType
from apps.workspaces.domain.workspace import WorkspaceArbitrary
from apps.workspaces.service import workspace
from config import settings
from infrastructure.storage.storage_arbitrary import (
    ArbitraryAzureStorageClient,
    ArbitraryGCPStorageClient,
    ArbitraryS3StorageClient,
)
from infrastructure.storage.storage_client import StorageClient
from infrastructure.storage.storage_config import StorageConfig


async def select_answer_storage(
    *,
    applet_id: uuid.UUID | None = None,
    owner_id: uuid.UUID | None = None,
    session: AsyncSession,
) -> StorageClient:
    """
    Create a CDNClient based on arbitrary server info to the answer bucket.
    This should be the entrypoint for
    """

    service = workspace.WorkspaceService(session, uuid.uuid4())
    if applet_id:
        info = await service.get_arbitrary_info_if_use_arbitrary(applet_id)
    elif owner_id:
        info = await service.get_arbitrary_info_by_owner_id_if_use_arbitrary(owner_id)
    else:
        raise ValueError("Applet id or owner id should be specified.")

    return create_answer_client(info)


def create_answer_client(info: WorkspaceArbitrary | None) -> StorageClient:
    """Create a CDN client based on optional arbitrary server info"""

    # No arbitrary server, create a client based on local configuration
    if not info:
        config_cdn = StorageConfig(
            endpoint_url=settings.cdn.endpoint_url,
            region=settings.cdn.region,
            bucket=settings.cdn.bucket_answer,
            ttl_signed_urls=settings.cdn.ttl_signed_urls,
            access_key=settings.cdn.access_key,
            secret_key=settings.cdn.secret_key,
        )
        return StorageClient(config_cdn, env=settings.env, max_concurrent_tasks=settings.cdn.max_concurrent_tasks)

    # Create an arbitrary server client
    bucket_type = info.storage_type.lower()
    arbitrary_cdn_config = StorageConfig(
        region=info.storage_region,
        bucket=info.storage_bucket,
        endpoint_url=info.storage_url,
        ttl_signed_urls=settings.cdn.ttl_signed_urls,
        access_key=info.storage_access_key,
        secret_key=info.storage_secret_key,
    )

    match bucket_type:
        case StorageType.AZURE:
            return ArbitraryAzureStorageClient(
                sec_key=info.storage_secret_key,
                bucket=str(info.storage_bucket),
                max_concurrent_tasks=settings.cdn.max_concurrent_tasks,
            )
        case StorageType.GCP:
            return ArbitraryGCPStorageClient(
                arbitrary_cdn_config,
                endpoint_url=settings.cdn.gcp_endpoint_url,
                env=settings.env,
                max_concurrent_tasks=settings.cdn.max_concurrent_tasks,
            )
        case _:
            # default is aws (logic from legacy app)
            return ArbitraryS3StorageClient(
                arbitrary_cdn_config, env=settings.env, max_concurrent_tasks=settings.cdn.max_concurrent_tasks
            )


async def get_media_storage() -> StorageClient:
    config = StorageConfig(
        endpoint_url=settings.cdn.endpoint_url,
        region=settings.cdn.region,
        bucket=settings.cdn.bucket,
        secret_key=settings.cdn.secret_key,
        access_key=settings.cdn.access_key,
        domain=settings.cdn.domain,
        ttl_signed_urls=settings.cdn.ttl_signed_urls,
    )
    return StorageClient(config, env=settings.env)


async def get_operations_storage() -> StorageClient:
    config = StorageConfig(
        endpoint_url=settings.cdn.endpoint_url,
        region=settings.cdn.region,
        bucket=settings.cdn.bucket_operations,
        secret_key=settings.cdn.secret_key,
        access_key=settings.cdn.access_key,
        domain=settings.cdn.domain,
        ttl_signed_urls=settings.cdn.ttl_signed_urls,
    )
    return StorageClient(config, env=settings.env)


async def get_log_storage() -> StorageClient:
    config = StorageConfig(
        endpoint_url=settings.cdn.endpoint_url,
        access_key=settings.cdn.access_key,
        secret_key=settings.cdn.secret_key,
        region=settings.cdn.region,
        bucket=settings.cdn.bucket_answer,
        ttl_signed_urls=settings.cdn.ttl_signed_urls,
    )
    return StorageClient(config, env=settings.env)
