# The applet must already be created
from fastapi import APIRouter, Body

from apps.permissions.domain import UserAppletAccessCreate, PublicUserAppletAccess, UserAppletAccess
from apps.permissions.errors import UserAppletAccessesError
from apps.permissions.services.crud import PermissionsCRUD
from apps.shared.domain import Response

router = APIRouter(prefix="/perm", tags=["Permissions"])


@router.post("/create", tags=["Permissions"])
async def create_permission(
    permission_create_schema: UserAppletAccessCreate = Body(...),
) -> Response[PublicUserAppletAccess]:
    try:
        permission: UserAppletAccess = await PermissionsCRUD().get_by_all(
            user_id_=permission_create_schema.user_id,
            applet_id_=permission_create_schema.applet_id,
            role=permission_create_schema.role
        )
        if permission:
            raise UserAppletAccessesError(message="Permission already exist")
    except UserAppletAccessesError:
        permission_in_db = UserAppletAccessCreate(
            user_id_=permission_create_schema.user_id,
            applet_id_=permission_create_schema.applet_id,
            role=permission_create_schema.role,
        )
        permission, _ = await PermissionsCRUD().save_user_permission(schema=permission_in_db)

    # Create public permission model
    public_permission = PublicUserAppletAccess(**permission.dict())

    return Response(result=public_permission)

# Something must beat for batch distribution of rights/permissions
