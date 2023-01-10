from fastapi import Body, Depends

from apps.applets.crud.applets import AppletsCRUD
from apps.applets.crud.roles import UserAppletAccessCRUD
from apps.applets.domain import (
    Applet,
    PublicApplet,
    AppletCreate,
    AppletUpdate,
    UserAppletAccessCreate,
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
        schema: AppletCreate = Body(...),
) -> Response[PublicApplet]:
    applet: Applet = await AppletsCRUD().save(user.id, schema=schema)

    await UserAppletAccessCRUD().save(
        schema=UserAppletAccessCreate(
            user_id=user.id,
            applet_id=applet.id,
            role=Role.ADMIN,
        )
    )

    return Response(result=PublicApplet(**applet.dict()))


async def applet_update(
        id_: int,
        user: User = Depends(get_current_user),
        schema: AppletUpdate = Body(...),
) -> Response[PublicApplet]:
    applet: Applet = await AppletsCRUD().update_applet(user.id, id_, schema)

    return Response(result=PublicApplet(**applet.dict()))


# TODO: Add logic to return concrete applets by user
async def applet_retrieve(
        id_: int, user: User = Depends(get_current_user)
) -> Response[PublicApplet]:
    applet: Applet = await AppletsCRUD().get_full_by_id(id_=id_)
    return Response(result=PublicApplet(**applet.dict()))


async def applet_list(
        user: User = Depends(get_current_user),
) -> ResponseMulti[Applet]:
    applets: list[Applet] = await AppletsCRUD().get_admin_applets(user.id)
    public_applets: list[PublicApplet] = []
    for applet in applets:
        public_applets.append(PublicApplet(**applet.dict()))
    return ResponseMulti(results=public_applets)


# TODO: Restrict by permissions
async def applet_delete(id_: int, user: User = Depends(get_current_user)):
    await AppletsCRUD().delete_by_id(id_=id_)
    raise NotContentError
