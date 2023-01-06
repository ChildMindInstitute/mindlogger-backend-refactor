from fastapi import Body, Depends

import apps.applets.domain as domain
from apps.applets.crud.applets import AppletsCRUD
from apps.applets.crud.roles import UserAppletAccessCRUD
from apps.applets.domain.constants import Role
from apps.authentication.deps import get_current_user
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.errors import NotContentError
from apps.users.domain import User


# TODO: Add logic to allow to create applets by permissions
# TODO: Restrict by admin
async def create_applet(
    user: User = Depends(get_current_user),
    schema: domain.applet_create.AppletCreate = Body(...),
) -> Response[domain.applet.Applet]:
    applet: domain.applet.Applet = await AppletsCRUD().save(
        user.id, schema=schema
    )

    await UserAppletAccessCRUD().save(
        schema=domain.UserAppletAccessCreate(
            user_id=user.id,
            applet_id=applet.id,
            role=Role.ADMIN,
        )
    )

    return Response(result=domain.applet.Applet(**applet.dict()))


async def update_applet(
    id_: int,
    user: User = Depends(get_current_user),
    schema: domain.applet_update.AppletUpdate = Body(...),
) -> Response[domain.applet.Applet]:
    applet: domain.applet.Applet = await AppletsCRUD().update_applet(
        user.id, id_, schema
    )

    return Response(result=domain.applet.Applet(**applet.dict()))


# TODO: Add logic to return concrete applets by user
async def get_applet_by_id(
    id_: int, user: User = Depends(get_current_user)
) -> Response[domain.applet.Applet]:
    applet: domain.applet.Applet = await AppletsCRUD().get_full_by_id(id_=id_)
    public_applet = domain.applet.PublicApplet(**applet.dict())
    return Response(result=public_applet)


async def get_applets(
    user: User = Depends(get_current_user),
) -> ResponseMulti[domain.applet.Applet]:
    applets: list[
        domain.applet.Applet
    ] = await AppletsCRUD().get_admin_applets(user.id)

    return ResponseMulti(results=applets)


# TODO: Restrict by permissions
async def delete_applet_by_id(
    id_: int, user: User = Depends(get_current_user)
):
    await AppletsCRUD().delete_by_id(id_=id_)
    raise NotContentError
