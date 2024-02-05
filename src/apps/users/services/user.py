import uuid

from apps.authentication.services import AuthenticationService
from apps.shared.hashing import hash_sha224
from apps.users import UserSchema, UsersCRUD
from apps.users.domain import User, UserCreate
from apps.users.errors import UserNotFound
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.db.schemas import UserWorkspaceSchema
from config import settings


class UserService:
    def __init__(self, session) -> None:
        self.session = session

    # TODO: Remove later, keep for now for backward compatibility for tests
    async def create_superuser(self, uuid_: uuid.UUID = uuid.uuid4()) -> None:
        crud = UsersCRUD(self.session)
        super_admin = await crud.get_super_admin()
        # Let's keep this frozen feature
        if super_admin is None:
            super_admin = UserSchema(
                id=uuid_,
                email=hash_sha224(settings.super_admin.email),
                first_name=settings.super_admin.first_name,
                last_name=settings.super_admin.last_name,
                hashed_password=AuthenticationService.get_password_hash(settings.super_admin.password),
                email_encrypted=settings.super_admin.email,
                is_super_admin=True,
            )
            user = await crud.save(super_admin)
            workspace = UserWorkspaceSchema(
                user_id=user.id,
                workspace_name=f"{user.first_name} {user.last_name}",
                is_modified=False,
            )
            await UserWorkspaceCRUD(self.session).save(schema=workspace)

    # TODO: Remove later, keep for now for backward compatibility for tests
    async def create_anonymous_respondent(self, uuid_: uuid.UUID = uuid.uuid4()) -> None:
        crud = UsersCRUD(self.session)
        anonymous_respondent = await crud.get_anonymous_respondent()
        if not anonymous_respondent:
            anonymous_respondent = UserSchema(
                id=uuid_,
                email=hash_sha224(settings.anonymous_respondent.email),
                first_name=settings.anonymous_respondent.first_name,
                last_name=settings.anonymous_respondent.last_name,
                hashed_password=AuthenticationService(self.session).get_password_hash(
                    settings.anonymous_respondent.password
                ),
                email_encrypted=settings.anonymous_respondent.email,
                is_anonymous_respondent=True,
            )
            await crud.save(anonymous_respondent)

    async def create_user(self, data: UserCreate) -> User:
        user_schema = await UsersCRUD(self.session).save(
            UserSchema(
                email=data.hashed_email,
                first_name=data.first_name,
                last_name=data.last_name,
                hashed_password=data.hashed_password,
                email_encrypted=data.email,
            )
        )

        user: User = User.from_orm(user_schema)
        return user

    async def get_by_email(self, email: str) -> User:
        crud = UsersCRUD(self.session)
        return await crud.get_by_email(email)

    async def exists_by_id(self, user_id: uuid.UUID) -> None:
        user_exist = await UsersCRUD(self.session).exist_by_id(id_=user_id)
        if not user_exist:
            raise UserNotFound()

    async def get(self, user_id: uuid.UUID) -> User:
        return await UsersCRUD(self.session).get_by_id(user_id)
