import uuid

from fastapi import Depends

from apps.applets.service import AppletService
from apps.authentication.deps import get_current_user
from apps.folders.domain import FolderCreate, FolderPublic, FolderUpdate
from apps.folders.service import FolderService
from apps.shared.domain import Response, ResponseMulti
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic, session_manager

__all__ = [
    "folder_list",
    "folder_create",
    "folder_update_name",
    "folder_delete",
    "folder_pin",
    "folder_unpin",
]


async def folder_list(
    workspace_id: uuid.UUID,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[FolderPublic]:
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(workspace_id)
        folders = await FolderService(session, workspace_id, user.id).list()
    return ResponseMulti(
        result=[FolderPublic.from_orm(f) for f in folders], count=len(folders)
    )


async def folder_create(
    workspace_id: uuid.UUID,
    data: FolderCreate,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[FolderPublic]:
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(workspace_id)
        folder = await FolderService(session, workspace_id, user.id).create(
            data
        )
    return Response(result=FolderPublic.from_orm(folder))


async def folder_update_name(
    workspace_id: uuid.UUID,
    folder_id: uuid.UUID,
    data: FolderUpdate,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[FolderPublic]:
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(workspace_id)
        folder = await FolderService(session, workspace_id, user.id).update(
            folder_id, data
        )
    return Response(result=FolderPublic.from_orm(folder))


async def folder_delete(
    workspace_id: uuid.UUID,
    folder_id: uuid.UUID,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(workspace_id)
        await FolderService(session, workspace_id, user.id).delete_by_id(
            folder_id
        )


async def folder_pin(
    workspace_id: uuid.UUID,
    folder_id: uuid.UUID,
    applet_id: uuid.UUID,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await AppletService(session, workspace_id).exist_by_id(applet_id)
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(workspace_id)
        await FolderService(session, workspace_id, user.id).pin_applet(
            folder_id, applet_id
        )


async def folder_unpin(
    workspace_id: uuid.UUID,
    folder_id: uuid.UUID,
    applet_id: uuid.UUID,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await AppletService(session, workspace_id).exist_by_id(applet_id)
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(workspace_id)
        await FolderService(session, workspace_id, user.id).unpin_applet(
            folder_id, applet_id
        )
