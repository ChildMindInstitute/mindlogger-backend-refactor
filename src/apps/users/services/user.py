from apps.authentication.services import AuthenticationService
from apps.users import UserSchema, UsersCRUD
from apps.users.domain import User
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD
from apps.workspaces.db.schemas import UserWorkspaceSchema
from config import settings


class UserService:
    def __init__(self, session):
        self.session = session

    async def create_superuser(self):
        crud = UsersCRUD(self.session)
        super_admin = await crud.get_super_admin()
        if super_admin is not None:
            if not settings.super_admin.force_update:
                return
            super_admin.email = settings.super_admin.email
            super_admin.first_name = settings.super_admin.first_name
            super_admin.last_name = settings.super_admin.last_name
            super_admin.hashed_password = AuthenticationService(
                self.session
            ).get_password_hash(settings.super_admin.password)
            super_admin.is_super_admin = True
            user = await crud.update_by_id(super_admin.id, super_admin)
        else:
            super_admin = UserSchema(
                email=settings.super_admin.email,
                first_name=settings.super_admin.first_name,
                last_name=settings.super_admin.last_name,
                hashed_password=AuthenticationService(
                    self.session
                ).get_password_hash(settings.super_admin.password),
                is_super_admin=True,
            )
            user = await crud.save(super_admin)
        workspace = await UserWorkspaceCRUD(self.session).get_by_user_id(
            user.id
        )
        if workspace:
            workspace.user_id = user.id
            workspace.workspace_name = f"{user.first_name} {user.last_name}"
            workspace.is_modified = False
            await UserWorkspaceCRUD(self.session).update_by_user_id(
                user.id, schema=workspace
            )
        else:
            workspace = UserWorkspaceSchema(
                user_id=user.id,
                workspace_name=f"{user.first_name} {user.last_name}",
                is_modified=False,
            )
            await UserWorkspaceCRUD(self.session).save(schema=workspace)

    async def create_anonymous_respondent(self):
        crud = UsersCRUD(self.session)
        anonymous_respondent = await crud.get_anonymous_respondent()
        if anonymous_respondent is not None:
            if not settings.anonymous_respondent.force_update:
                return
            anonymous_respondent.email = settings.anonymous_respondent.email
            anonymous_respondent.first_name = (
                settings.anonymous_respondent.first_name
            )
            anonymous_respondent.last_name = (
                settings.anonymous_respondent.last_name
            )
            anonymous_respondent.hashed_password = AuthenticationService(
                self.session
            ).get_password_hash(settings.anonymous_respondent.password)
            anonymous_respondent.is_anonymous_respondent = True
            await crud.update_by_id(
                anonymous_respondent.id, anonymous_respondent
            )
        else:
            anonymous_respondent = UserSchema(
                email=settings.anonymous_respondent.email,
                first_name=settings.anonymous_respondent.first_name,
                last_name=settings.anonymous_respondent.last_name,
                hashed_password=AuthenticationService(
                    self.session
                ).get_password_hash(settings.anonymous_respondent.password),
                is_anonymous_respondent=True,
            )
            await crud.save(anonymous_respondent)

    async def get_by_email(self, email: str) -> User:
        crud = UsersCRUD(self.session)
        return await crud.get_by_email(email)
