from fastapi import Body, Depends

from apps.applets.crud.applets import AppletsCRUD
from apps.applets.crud.roles import UserAppletAccessCRUD
from apps.applets.domain.applets import (
    Applet,
    AppletCreate,
    AppletCreateRequest,
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
    applet_create_schema: AppletCreateRequest = Body(...),
) -> Response[PublicApplet]:
    schema: AppletCreate = AppletCreate(
        display_name=applet_create_schema.display_name,
        description=applet_create_schema.description,
    )
    applet: Applet = await AppletsCRUD().save(schema=schema)

    await UserAppletAccessCRUD().save(
        schema=UserAppletAccessCreate(
            user_id=user.id, applet_id=applet.id, role=Role.ADMIN
        )
    )

    return Response(result=PublicApplet(**applet.dict()))


async def get_applet_by_id(
    id: int, user: User = Depends(get_current_user)
) -> Response[PublicApplet]:
    applet: Applet = await AppletsCRUD().get_by_id(id_=id)
    public_applet = PublicApplet(**applet.dict())
    return Response(result=public_applet)


async def get_applets(
    user: User = Depends(get_current_user),
) -> ResponseMulti[Applet]:
    applets: list[Applet] = await AppletsCRUD().get_admin_applets(user.id)

    return ResponseMulti(results=applets)


async def delete_applet_by_id(id: int, user: User = Depends(get_current_user)):
    await AppletsCRUD().get_by_id(id_=id)
    await AppletsCRUD().delete_by_id(id_=id)
    raise NotContentError
