from fastapi import Body, Depends

from apps.applets.crud.applets import AppletsCRUD
from apps.applets.crud.roles import UserAppletAccessCRUD
from apps.applets.domain.applets import (
    Applet,
    AppletCreate,
    PublicApplet,
    UserAppletAccessCreate,
)
from apps.applets.domain.constants import Role
from apps.authentication.deps import get_current_user
from apps.shared.domain.response import Response, ResponseMulti
from apps.shared.errors import NotContentError
from apps.users.domain import User


async def create_applet(
    user: User = Depends(get_current_user),
    schema: AppletCreate = Body(...),
) -> Response[PublicApplet]:
    applet: Applet = await AppletsCRUD().save(schema=schema)

    await UserAppletAccessCRUD().save(
        schema=UserAppletAccessCreate(
            user_id=user.id,
            applet_id=applet.id,
            role=Role.ADMIN,
        )
    )

    return Response(result=PublicApplet(**applet.dict()))


async def get_applet_by_id(
    id_: int, user: User = Depends(get_current_user)
) -> Response[PublicApplet]:
    applet: Applet = await AppletsCRUD().get_by_id(id_=id_)
    public_applet = PublicApplet(**applet.dict())

    return Response(result=public_applet)


async def get_applets(
    user: User = Depends(get_current_user),
) -> ResponseMulti[Applet]:
    """Returns all applets where the current user exists."""

    applets: list[Applet] = await AppletsCRUD().all(user.id)

    return ResponseMulti(results=applets)


# TODO: Restrict by permissions
async def delete_applet_by_id(
    id_: int, user: User = Depends(get_current_user)
):
    await AppletsCRUD().delete_by_id(id_=id_)
    raise NotContentError
