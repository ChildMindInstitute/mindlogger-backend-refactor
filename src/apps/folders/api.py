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
]


async def folder_list(
    user=Depends(get_current_user),
) -> ResponseMulti[FolderPublic]:
    folders = await FolderService(user.id).list()
    return ResponseMulti(results=[FolderPublic.from_orm(f) for f in folders])


async def folder_create(
    data: FolderCreate, user=Depends(get_current_user)
) -> Response[FolderPublic]:
    folder = await FolderService(user.id).create(data)
    return Response(result=FolderPublic.from_orm(folder))


async def folder_update_name(
    id_: int, data: FolderUpdate, user=Depends(get_current_user)
) -> Response[FolderPublic]:
    folder = await FolderService(user.id).update(id_, data)
    return Response(result=FolderPublic.from_orm(folder))


async def folder_delete(id_: int, user=Depends(get_current_user)):
    await FolderService(user.id).delete_by_id(id_)
