from fastapi import Body, Depends
from fastapi.routing import APIRouter

from apps.applets.domain import (
    Applet,
    AppletCreate,
    AppletCreateRequest,
    PublicApplet,
)
from apps.applets.errors import AppletsError, AppletsNotFoundError
from apps.applets.services.crud import AppletsCRUD
from apps.authentication.deps import get_current_user
from apps.authentication.errors import BadCredentials
from apps.authentication.services.crud import TokensCRUD
from apps.shared.domain.response import Response
from apps.users.db import Role
from apps.users.domain import User, UserAppletAccessCreate
from apps.users.errors import UsersError
from apps.users.services import PermissionsCRUD

router = APIRouter(tags=["Applets"])


@router.post("/applet/create", tags=["Applets"])
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

        await PermissionsCRUD().save_user_permission(
            schema=UserAppletAccessCreate(
                user_id=user.id, applet_id=applet.id, role=Role("admin")
            )
        )
    public_applet = PublicApplet(**applet.dict())

    return Response(result=public_applet)


@router.get("/applet/{id}", tags=["Applets"])
async def get_applet_by_id(
    id: int,
    user: User = Depends(get_current_user),
) -> Response[list[PublicApplet]]:
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


@router.get("/applets", tags=["Applets"])
async def get_applet_user_admin(
    user: User = Depends(get_current_user),
) -> Response[list[Applet]]:
    access_token_not_correct = BadCredentials(
        message="Access token is not correct"
    )
    try:
        await TokensCRUD().get_by_email(email=user.email)
    except UsersError:
        raise access_token_not_correct

    applets: list[Applet] = await AppletsCRUD().get_by_user_id_role_admin(
        user.id
    )
    return Response(result=applets)
