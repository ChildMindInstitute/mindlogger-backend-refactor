import uuid
from typing import Union

from sqlalchemy.ext.asyncio import AsyncSession

from apps.file.services import AzurePresignService, GCPPresignService, S3PresignService
from apps.workspaces.constants import StorageType
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.workspace import WorkspaceService


async def get_presign_service(
    applet_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> Union[S3PresignService, GCPPresignService, AzurePresignService]:
    wsp_service = WorkspaceService(session, user_id)
    arbitrary_info = await wsp_service.get_arbitrary_info_if_use_arbitrary(applet_id)
    access = await UserAppletAccessCRUD(session).get_by_roles(
        user_id,
        applet_id,
        [Role.OWNER, Role.MANAGER, Role.REVIEWER, Role.RESPONDENT],
    )
    if arbitrary_info:
        if arbitrary_info.storage_type.lower() == StorageType.AZURE:
            return AzurePresignService(
                session,
                user_id,
                applet_id,
                access,
            )
        if arbitrary_info.storage_type.lower() == StorageType.GCP:
            return GCPPresignService(session, user_id, applet_id, access)
    return S3PresignService(session, user_id, applet_id, access)
