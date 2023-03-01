from sqlalchemy import select
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query

from apps.users import User
from apps.workspaces.db.schemas import UserWorkspaceSchema
from apps.workspaces.domain.workspace import UserWorkspace
from infrastructure.database.crud import BaseCRUD

__all__ = ["UserWorkspaceCRUD"]


class UserWorkspaceCRUD(BaseCRUD[UserWorkspaceSchema]):
    schema_class = UserWorkspaceSchema

    async def get_by_user_id(self, user_id_: int) -> UserWorkspaceSchema:
        query: Query = select(self.schema_class).filter(
            self.schema_class.user_id == user_id_
        )
        result: Result = await self._execute(query)

        return result.scalars().one_or_none()

    async def save(self, schema: UserWorkspaceSchema) -> UserWorkspaceSchema:
        """Return UserWorkspace instance."""
        return await self._create(schema)

    async def update(
        self, user: User, workspace_prefix: str | None = None
    ) -> UserWorkspace:
        # Update UserWorkspace in database
        instance = await self._update_one(
            lookup="user_id",
            value=user.id,
            schema=UserWorkspaceSchema(
                user_id=user.id,
                workspace_name=f"{user.first_name} {user.last_name} "
                f"{workspace_prefix}"
                if workspace_prefix
                else f"{user.first_name} {user.last_name}",
                is_modified=True,
            ),
        )

        # Create internal data model
        user_workspace = UserWorkspace.from_orm(instance)

        return user_workspace
