import uuid

from sqlalchemy import and_, select
from sqlalchemy.orm import Query

from apps.applets.db.schemas.applet import AppletSchema
from apps.workspaces.db.schemas.user_applet_access import (
    UserAppletAccessSchema,
)
from apps.workspaces.db.schemas.user_workspace import (
    UserWorkspaceArbitrary,
    UserWorkspaceSchema,
)
from apps.workspaces.domain.constants import Role
from infrastructure.database.crud import BaseCRUD

__all__ = ["UserWorkspaceArbitraryCRUD"]


class UserWorkspaceArbitraryCRUD(BaseCRUD[UserWorkspaceArbitrary]):
    schema_class = UserWorkspaceArbitrary

    async def get_by_workspace(
        self, user_workspace_id: uuid.UUID
    ) -> UserWorkspaceArbitrary | None:
        query: Query = select(UserWorkspaceArbitrary).filter(
            user_workspace_id == user_workspace_id
        )
        db_result = await self._execute(query)
        return db_result.scalars().first()

    async def delete(self, pk: uuid.UUID):
        await self._delete("id", pk)

    async def get_by_applet(self, applet_id: uuid.UUID):
        query: Query = select(UserWorkspaceArbitrary)
        query = query.select_from(AppletSchema)
        query.join(
            UserAppletAccessSchema,
            and_(
                UserAppletAccessSchema.applet_id == AppletSchema.id,
                UserAppletAccessSchema.role == Role.OWNER,
            ),
        )
        query.join(
            UserWorkspaceSchema,
            UserWorkspaceSchema.user_id == UserAppletAccessSchema.user_id,
        )
        query.join(
            UserWorkspaceArbitrary,
            UserWorkspaceArbitrary.user_workspace_id == UserWorkspaceSchema.id,
        )
        query = query.where(
            AppletSchema.id == applet_id,
            UserWorkspaceArbitrary.use_arbitrary.is_(True),
        )
        res = await self._execute(query)
        return res.scalars().first()
