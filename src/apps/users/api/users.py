from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.authentication.services import AuthenticationService
from apps.shared.domain.response import Response
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import (
    PublicUser,
    User,
    UserCreate,
    UserCreateRequest,
    UserUpdateRequest,
)
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.db.schemas import UserWorkspaceSchema
from infrastructure.database import session_manager
from infrastructure.database.core import atomic


async def user_create(
    user_create_schema: UserCreateRequest = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[PublicUser]:
    async with atomic(session):
        user_create = UserCreate(
            email=user_create_schema.email,
            first_name=user_create_schema.first_name,
            last_name=user_create_schema.last_name,
            hashed_password=AuthenticationService.get_password_hash(
                user_create_schema.password
            ),
        )
        user, _ = await UsersCRUD(session).save(schema=user_create)

        # Create public user model in order to avoid password sharing
        public_user = PublicUser(**user.dict())

        # Create default workspace for new user
        user_workspace = UserWorkspaceSchema(
            user_id=user.id,
            workspace_name=f"{user.first_name} {user.last_name}",
            is_modified=False,
        )
        await UserWorkspaceCRUD(session).save(schema=user_workspace)

    return Response(result=public_user)


async def user_retrieve(
    user: User = Depends(get_current_user),
) -> Response[PublicUser]:
    # Get public representation of the authenticated user
    public_user = PublicUser(**user.dict())

    return Response(result=public_user)


async def user_update(
    user: User = Depends(get_current_user),
    user_update_schema: UserUpdateRequest = Body(...),
    session=Depends(session_manager.get_session),
) -> Response[PublicUser]:
    async with atomic(session):
        updated_user: User = await UsersCRUD(session).update(
            user, user_update_schema
        )

    # Create public representation of the internal user
    public_user = PublicUser(**updated_user.dict())

    return Response(result=public_user)


async def user_delete(
    user: User = Depends(get_current_user),
    session=Depends(session_manager.get_session),
) -> None:
    async with atomic(session):
        await UsersCRUD(session).delete(user)
