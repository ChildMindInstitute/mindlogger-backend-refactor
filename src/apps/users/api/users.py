from fastapi import Body, Depends
from pydantic import ValidationError

from apps.authentication.deps import get_current_user
from apps.authentication.services import AuthenticationService
from apps.shared.domain.response import Response
from apps.shared.encryption import encrypt
from apps.shared.hashing import hash_sha224
from apps.users import UserSchema
from apps.users.cruds.user import UsersCRUD
from apps.users.domain import (
    PublicUser,
    User,
    UserCreateRequest,
    UserUpdateRequest,
)
from apps.users.errors import EmailAddressNotValid
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.db.schemas import UserWorkspaceSchema
from infrastructure.database.core import atomic
from infrastructure.database.deps import get_session


async def user_create(
    user_create_schema: UserCreateRequest = Body(...),
    session=Depends(get_session),
) -> Response[PublicUser]:
    async with atomic(session):
        email_hash = hash_sha224(user_create_schema.email)
        email_aes_encrypted = encrypt(bytes(user_create_schema.email, "utf-8"))

        user_schema = await UsersCRUD(session).save(
            UserSchema(
                email=email_hash,
                first_name=user_create_schema.encrypted_first_name,
                last_name=user_create_schema.encrypted_last_name,
                hashed_password=AuthenticationService.get_password_hash(
                    user_create_schema.password
                ),
                email_aes_encrypted=email_aes_encrypted,
            )
        )

        user: User = User.from_orm(user_schema)

        try:
            public_user = PublicUser.from_user(user)
        except ValidationError:
            raise EmailAddressNotValid(email=user_create_schema.email)

        # Create default workspace for new user
        workspace_name = f"{user.plain_first_name} {user.plain_last_name}"
        workspace_name_encrypted = encrypt(
            bytes(workspace_name, "utf-8")
        ).hex()
        user_workspace = UserWorkspaceSchema(
            user_id=user.id,
            workspace_name=workspace_name_encrypted,
            is_modified=False,
        )
        await UserWorkspaceCRUD(session).save(schema=user_workspace)

    return Response(result=public_user)


async def user_retrieve(
    user: User = Depends(get_current_user),
) -> Response[PublicUser]:
    # Get public representation of the authenticated user
    public_user = PublicUser.from_user(user)

    return Response(result=public_user)


async def user_update(
    user: User = Depends(get_current_user),
    user_update_schema: UserUpdateRequest = Body(...),
    session=Depends(get_session),
) -> Response[PublicUser]:
    async with atomic(session):
        updated_user: User = await UsersCRUD(session).update(
            user, user_update_schema
        )

    # Create public representation of the internal user
    public_user = PublicUser.from_user(updated_user)

    return Response(result=public_user)


async def user_delete(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> None:
    async with atomic(session):
        await UsersCRUD(session).delete(user)
