from fastapi import Body, Depends

from apps.applets.domain import (
    AppletFolder,
    PublicAppletHistoryChange,
    PublicHistory,
)
from apps.applets.domain.applet_link import AppletLink, CreateAccessLink
from apps.applets.domain.applets import public_detail, public_history_detail
from apps.applets.domain.applets.applet import AppletName, AppletUniqueName
from apps.applets.domain.applets.create import AppletCreate
from apps.applets.domain.applets.update import AppletUpdate
from apps.applets.service import AppletHistoryService, AppletService
from apps.applets.service.applet import (
    create_applet,
    get_admin_applets,
    retrieve_applet,
    update_applet,
)
from apps.applets.service.applet_history import (
    retrieve_applet_by_version,
    retrieve_versions,
)
from apps.authentication.deps import get_current_user
from apps.shared.domain.response import Response, ResponseMulti
from apps.users.domain import User

__all__ = [
    "applet_create",
    "applet_update",
    "applet_retrieve",
    "applet_versions_retrieve",
    "applet_version_retrieve",
    "applet_version_changes_retrieve",
    "applet_list",
    "applet_delete",
    "applet_set_folder",
    "folders_applet_get",
    "applet_unique_name_get",
    "applet_link_create",
    "applet_link_get",
    "applet_link_delete",
]


# TODO: Add logic to allow to create applets by permissions
# TODO: Restrict by admin
async def applet_create(
    user: User = Depends(get_current_user),
    schema: AppletCreate = Body(...),
) -> Response[public_detail.Applet]:
    applet = await create_applet(schema, user.id)
    return Response(result=public_detail.Applet(**applet.dict()))


async def applet_update(
    id_: int,
    user: User = Depends(get_current_user),
    schema: AppletUpdate = Body(...),
) -> Response[public_detail.Applet]:
    applet = await update_applet(id_, schema, user.id)
    return Response(result=public_detail.Applet(**applet.dict()))


# TODO: Add logic to return concrete applets by user
async def applet_retrieve(
    id_: int, user: User = Depends(get_current_user)
) -> Response[public_detail.Applet]:
    applet = await retrieve_applet(user.id, id_)
    return Response(result=public_detail.Applet(**applet.dict()))


async def applet_versions_retrieve(
    id_: int, user: User = Depends(get_current_user)
) -> ResponseMulti[PublicHistory]:
    histories = await retrieve_versions(id_)
    return ResponseMulti(result=[PublicHistory(**h.dict()) for h in histories])


async def applet_version_retrieve(
    id_: int, version: str, user: User = Depends(get_current_user)
) -> Response[public_history_detail.AppletDetailHistory]:
    applet = await retrieve_applet_by_version(id_, version)
    if not applet:
        return Response(result=None)
    return Response(
        result=public_history_detail.AppletDetailHistory(**applet.dict())
    )


async def applet_version_changes_retrieve(
    id_: int, version: str, user: User = Depends(get_current_user)
) -> Response[PublicAppletHistoryChange]:
    changes = await AppletHistoryService(id_, version).get_changes()
    return Response(result=PublicAppletHistoryChange(**changes.dict()))


async def applet_list(
    user: User = Depends(get_current_user),
) -> ResponseMulti[public_detail.Applet]:
    applets = await get_admin_applets(user.id)
    public_applets: list[public_detail.Applet] = []
    for applet in applets:
        public_applets.append(public_detail.Applet(**applet.dict()))
    return ResponseMulti(result=public_applets)


async def applet_delete(id_: int, user: User = Depends(get_current_user)):
    await AppletService(user.id).delete_applet_by_id(id_)


async def applet_set_folder(
    applet_folder: AppletFolder, user: User = Depends(get_current_user)
):
    await AppletService(user.id).set_applet_folder(applet_folder)


async def folders_applet_get(
    id_: int, user: User = Depends(get_current_user)
) -> ResponseMulti[public_detail.Applet]:
    applets = await AppletService(user.id).get_folder_applets(id_)
    return ResponseMulti(
        result=[public_detail.Applet.from_orm(applet) for applet in applets]
    )


async def applet_unique_name_get(
    schema: AppletName = Body(...), user: User = Depends(get_current_user)
) -> Response[AppletUniqueName]:
    new_name = await AppletService(user.id).get_unique_name(schema)
    return Response(result=AppletUniqueName(name=new_name))


async def applet_link_create(
    id_: int,
    user: User = Depends(get_current_user),
    schema: CreateAccessLink = Body(...),
) -> Response[AppletLink]:
    access_link = await AppletService(user.id).create_access_link(
        applet_id=id_, create_request=schema
    )
    return Response(result=access_link)


async def applet_link_get(
    id_: int,
    user: User = Depends(get_current_user),
) -> Response[AppletLink]:
    access_link = await AppletService(user.id).get_access_link(applet_id=id_)
    return Response(result=access_link)


async def applet_link_delete(
    id_: int,
    user: User = Depends(get_current_user),
):
    await AppletService(user.id).delete_access_link(applet_id=id_)
