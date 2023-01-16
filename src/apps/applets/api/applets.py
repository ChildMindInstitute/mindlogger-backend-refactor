from fastapi import Body, Depends

from apps.applets.crud import AppletHistoryCRUD, AppletsCRUD
from apps.applets.crud.roles import UserAppletAccessCRUD
from apps.applets.domain import (
    PublicHistory,
    UserAppletAccessCreate,
    creating_applet,
    detailing_public_applet,
    detailing_public_history,
    updating_applet,
)
from apps.applets.domain.constants import Role
from apps.authentication.deps import get_current_user
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.errors import NotContentError
from apps.users.domain import User


# TODO: Add logic to allow to create applets by permissions
# TODO: Restrict by admin
async def applet_create(
    user: User = Depends(get_current_user),
    schema: creating_applet.AppletCreate = Body(...),
) -> Response[detailing_public_applet.Applet]:
    applet = await AppletsCRUD().save(user.id, schema=schema)

    await UserAppletAccessCRUD().save(
        schema=UserAppletAccessCreate(
            user_id=user.id,
            applet_id=applet.id,
            role=Role.ADMIN,
        )
    )

    return Response(result=detailing_public_applet.Applet(**applet.dict()))


async def applet_update(
    id_: int,
    user: User = Depends(get_current_user),
    schema: updating_applet.AppletUpdate = Body(...),
) -> Response[detailing_public_applet.Applet]:
    applet = await AppletsCRUD().update_applet(user.id, id_, schema)

    return Response(result=detailing_public_applet.Applet(**applet.dict()))


# TODO: Add logic to return concrete applets by user
async def applet_retrieve(
    id_: int, user: User = Depends(get_current_user)
) -> Response[detailing_public_applet.Applet]:
    applet = await AppletsCRUD().get_full(applet_id=id_)
    return Response(result=detailing_public_applet.Applet(**applet.dict()))


async def applet_versions_retrieve(
    id_: int, user: User = Depends(get_current_user)
) -> ResponseMulti[PublicHistory]:
    histories = await AppletHistoryCRUD().histories_by_applet_id(id_)
    return ResponseMulti(
        results=[PublicHistory(**h.dict()) for h in histories]
    )


async def applet_version_retrieve(
    id_: int, version: str, user: User = Depends(get_current_user)
) -> Response[detailing_public_history.Applet]:
    applet = await AppletHistoryCRUD().get_full(id_, version)
    return Response(result=detailing_public_history.Applet(**applet.dict()))


async def applet_list(
    user: User = Depends(get_current_user),
) -> ResponseMulti[detailing_public_applet.Applet]:
    applets = await AppletsCRUD().get_admin_applets(user.id)
    public_applets: list[detailing_public_applet.Applet] = []
    for applet in applets:
        public_applets.append(detailing_public_applet.Applet(**applet.dict()))
    return ResponseMulti(results=public_applets)


# TODO: Restrict by permissions
async def applet_delete(id_: int, user: User = Depends(get_current_user)):
    await AppletsCRUD().delete_by_id(id_=id_)
    raise NotContentError
