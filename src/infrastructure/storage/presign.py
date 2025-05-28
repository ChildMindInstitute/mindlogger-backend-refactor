import uuid
from typing import Union

from sqlalchemy.ext.asyncio import AsyncSession

from apps.workspaces.constants import StorageType
from infrastructure.storage.storage import select_storage
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.storage.presign_services import S3PresignService, GCPPresignService, AzurePresignService


async def get_presign_service(
    applet_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> Union[S3PresignService, GCPPresignService, AzurePresignService]:
    """
    Asynchronously retrieves a presigned service instance for handling object storage
    operations based on the associated applet's storage type.  If the applet's workspace
    is configured to use an arbitrary storage provider, the appropriate service is created
    with the configured arbitrary credentials.  Otherwise, the service is created with regular
    credentials.

    Parameters:
    app_id : uuid.UUID
        The unique identifier of the applet for which the presigned service is
        requested.
    user_id : uuid.UUID
        The unique identifier of the user requesting the presigned service.
    session : AsyncSession
        An asynchronous database session used for interaction with the database.

    Returns:
    Union[S3PresignService, GCPPresignService, AzurePresignService]
        A presigned service instance appropriate for the applet's storage type,
        which can be AWS S3, Google Cloud Storage (GCP), or Azure Blob Storage,
        based on the applet's configuration.
    """
    wsp_service = WorkspaceService(session, user_id)
    arbitrary_info = await wsp_service.get_arbitrary_info_if_use_arbitrary(applet_id)

    access = await UserAppletAccessCRUD(session).get_by_roles(
        user_id,
        applet_id,
        [Role.OWNER, Role.MANAGER, Role.REVIEWER, Role.RESPONDENT],
    )

    cdn_client = await select_storage(applet_id=applet_id, session=session)

    if arbitrary_info:
        if arbitrary_info.storage_type.lower() == StorageType.AZURE:
            return AzurePresignService(
                session,
                user_id,
                applet_id,
                access,
                cdn_client
            )

        if arbitrary_info.storage_type.lower() == StorageType.GCP:
            return GCPPresignService(session, user_id, applet_id, access, cdn_client)

    return S3PresignService(session, user_id, applet_id, access, cdn_client)