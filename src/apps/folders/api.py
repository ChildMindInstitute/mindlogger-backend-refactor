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
    owner_id: uuid.UUID,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[FolderPublic]:
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(owner_id)
        folders = await FolderService(session, owner_id).list()
        folder_count = await FolderService(session, owner_id).count()
    return ResponseMulti(
        result=[FolderPublic.from_orm(f) for f in folders], count=folder_count
    )


async def folder_create(
    owner_id: uuid.UUID,
    data: FolderCreate,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[FolderPublic]:
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(owner_id)
        folder = await FolderService(session, owner_id).create(data)
    return Response(result=FolderPublic.from_orm(folder))


async def folder_update_name(
    owner_id: uuid.UUID,
    folder_id: uuid.UUID,
    data: FolderUpdate,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[FolderPublic]:
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(owner_id)
        folder = await FolderService(session, user.id).update(folder_id, data)
    return Response(result=FolderPublic.from_orm(folder))


async def folder_delete(
    owner_id: uuid.UUID,
    folder_id: uuid.UUID,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(owner_id)
        await FolderService(session, owner_id).delete_by_id(folder_id)


async def folder_pin(
    owner_id: uuid.UUID,
    folder_id: uuid.UUID,
    applet_id: uuid.UUID,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(owner_id)
        await AppletService(session, owner_id).exist_by_id(applet_id)
        await FolderService(session, owner_id).pin_applet(
            id_=folder_id, applet_id=applet_id
        )


async def folder_unpin(
    owner_id: uuid.UUID,
    folder_id: uuid.UUID,
    applet_id: uuid.UUID,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await CheckAccessService(
            session, user.id
        ).check_workspace_folder_access(owner_id)
        await AppletService(session, owner_id).exist_by_id(applet_id)
        await FolderService(session, owner_id).unpin_applet(
            id_=folder_id, applet_id=applet_id
        )
