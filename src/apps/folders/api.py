import uuid

from fastapi import Depends

from apps.authentication.deps import get_current_user
from apps.folders.domain import FolderCreate, FolderPublic, FolderUpdate
from apps.folders.service import FolderService
from apps.shared.domain import Response, ResponseMulti

__all__ = [
    "folder_list",
    "folder_create",
    "folder_update_name",
    "folder_delete",
    "folder_pin",
    "folder_unpin",
]

from infrastructure.database import atomic, session_manager


async def folder_list(
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> ResponseMulti[FolderPublic]:
    async with atomic(session):
        folders = await FolderService(session, user.id).list()
    return ResponseMulti(result=[FolderPublic.from_orm(f) for f in folders])


async def folder_create(
    data: FolderCreate,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[FolderPublic]:
    async with atomic(session):
        folder = await FolderService(session, user.id).create(data)
    return Response(result=FolderPublic.from_orm(folder))


async def folder_update_name(
    id_: uuid.UUID,
    data: FolderUpdate,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> Response[FolderPublic]:
    async with atomic(session):
        folder = await FolderService(session, user.id).update(id_, data)
    return Response(result=FolderPublic.from_orm(folder))


async def folder_delete(
    id_: uuid.UUID,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await FolderService(session, user.id).delete_by_id(id_)


async def folder_pin(
    id_: uuid.UUID,
    applet_id: uuid.UUID,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await FolderService(session, user.id).pin_applet(
            id_=id_, applet_id=applet_id
        )


async def folder_unpin(
    id_: uuid.UUID,
    applet_id: uuid.UUID,
    user=Depends(get_current_user),
    session=Depends(session_manager.get_session),
):
    async with atomic(session):
        await FolderService(session, user.id).unpin_applet(
            id_=id_, applet_id=applet_id
        )
