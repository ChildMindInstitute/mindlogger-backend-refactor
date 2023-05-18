import uuid

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

    async def get_by_user_id(self, user_id_: uuid.UUID) -> UserWorkspaceSchema:
        query: Query = select(self.schema_class).filter(
            self.schema_class.user_id == user_id_
        )
        result: Result = await self._execute(query)

        return result.scalars().one_or_none()

    async def get_by_ids(
        self, ids: list[uuid.UUID]
    ) -> list[UserWorkspaceSchema]:
        query: Query = select(self.schema_class)
        query = query.filter(self.schema_class.user_id.in_(ids))
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def save(self, schema: UserWorkspaceSchema) -> UserWorkspaceSchema:
        """Return UserWorkspace instance."""
        return await self._create(schema)

    async def update(self, user: User, workspace_prefix: str) -> UserWorkspace:
        # Update UserWorkspace in database
        instance = await self._update_one(
            lookup="user_id",
            value=user.id,
            schema=UserWorkspaceSchema(
                user_id=user.id,
                workspace_name=workspace_prefix,
                is_modified=True,
            ),
        )

        # Create internal data model
        user_workspace = UserWorkspace.from_orm(instance)

        return user_workspace
