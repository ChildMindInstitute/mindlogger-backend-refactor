from fastapi import Body, Depends

from apps.applets.crud.applets import AppletsCRUD
from apps.applets.crud.roles import UserAppletAccessCRUD
from apps.applets.domain import (
    Applet,
    AppletCreate,
    AppletCreateRequest,
    PublicApplet,
)
from apps.applets.errors import AppletsError, AppletsNotFoundError
from apps.applets.services.constants import Role
from apps.authentication.crud import TokensCRUD
from apps.authentication.deps import get_current_user
from apps.authentication.errors import BadCredentials
from apps.shared.domain.response import Response, ResponseMulti
from apps.users.domain import User, UserAppletAccess, UserAppletAccessCreate
from apps.users.errors import UsersError


async def create_applet(
    user: User = Depends(get_current_user),
    applet_create_schema: AppletCreateRequest = Body(...),
) -> Response[PublicApplet]:
    access_token_not_correct = BadCredentials(
        message="Access token is not correct"
    )
    try:
        await TokensCRUD().get_by_email(email=user.email)
    except UsersError:
        raise access_token_not_correct

    try:
        await AppletsCRUD().get_by_display_name(
            display_name=applet_create_schema.display_name
        )
        raise AppletsError("Applet already exist")
    except AppletsNotFoundError:
        applet_in_db = AppletCreate(
            display_name=applet_create_schema.display_name,
            description=applet_create_schema.description,
        )
        # Save UserAppletAccess into the database
        applet, _ = await AppletsCRUD().save_applet(schema=applet_in_db)

        await UserAppletAccessCRUD().save_user_applet_access(
            schema=UserAppletAccessCreate(
                user_id=user.id, applet_id=applet.id, role=Role("admin")
            )
        )
    public_applet = PublicApplet(**applet.dict())

    return Response(result=public_applet)


async def get_applet_by_id(
    id: int,
    user: User = Depends(get_current_user),
) -> Response[PublicApplet]:
    access_token_not_correct = BadCredentials(
        message="Access token is not correct"
    )
    try:
        await TokensCRUD().get_by_email(email=user.email)
    except UsersError:
        raise access_token_not_correct

    try:
        applet: Applet = await AppletsCRUD().get_by_id(id_=id)
        public_applet = PublicApplet(**applet.dict())
        return Response(result=public_applet)
    except AppletsNotFoundError:
        raise AppletsNotFoundError(f"Applet with id={id} not found.")


async def get_user_applet_accesses_for_user_admin(
    user: User = Depends(get_current_user),
) -> ResponseMulti[list[UserAppletAccess]]:
    access_token_not_correct = BadCredentials(
        message="Access token is not correct"
    )
    try:
        await TokensCRUD().get_by_email(email=user.email)
    except UsersError:
        raise access_token_not_correct

    user_applet_accesses: list[
        UserAppletAccess
    ] = await UserAppletAccessCRUD().get_by_user_id_role_admin(user.id)

    return ResponseMulti(results=user_applet_accesses)


async def get_applets_user_admin(
    user: User = Depends(get_current_user),
) -> ResponseMulti[list[Applet]]:
    access_token_not_correct = BadCredentials(
        message="Access token is not correct"
    )
    try:
        await TokensCRUD().get_by_email(email=user.email)
    except UsersError:
        raise access_token_not_correct

    user_applet_accesses: list[
        Applet
    ] = await AppletsCRUD().get_by_user_id_role_admin(user.id)

    return ResponseMulti(results=user_applet_accesses)
