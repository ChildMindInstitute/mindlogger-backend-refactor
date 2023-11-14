import uuid

from pydantic import parse_obj_as
from sqlalchemy import and_, select
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query

from apps.applets.db.schemas import AppletSchema
from apps.workspaces.db.schemas import (
    UserAppletAccessSchema,
    UserWorkspaceSchema,
)
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.workspace import UserAnswersDBInfo
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

    async def get_all(self) -> list[UserWorkspaceSchema]:
        query: Query = select(self.schema_class)
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def save(self, schema: UserWorkspaceSchema) -> UserWorkspaceSchema:
        """Return UserWorkspace instance."""
        return await self._create(schema)

    async def update_by_user_id(
        self, user_id: uuid.UUID, schema: UserWorkspaceSchema
    ) -> UserWorkspaceSchema:
        instance = await self._update_one(
            lookup="user_id",
            value=user_id,
            schema=schema,
        )
        return instance

    async def get_by_applet_id(
        self, applet_id: uuid.UUID
    ) -> UserWorkspaceSchema | None:
        access_subquery: Query = select(UserAppletAccessSchema.owner_id)
        access_subquery = access_subquery.where(
            and_(
                UserAppletAccessSchema.role == Role.OWNER,
                UserAppletAccessSchema.applet_id == applet_id,
            )
        )
        access_subquery = access_subquery.subquery()

        query: Query = select(UserWorkspaceSchema)
        query = query.where(UserWorkspaceSchema.user_id.in_(access_subquery))
        db_result = await self._execute(query)
        res = db_result.scalars().first()
        return res

    async def get_bucket_info(self, applet_id: uuid.UUID):
        query: Query = select(
            UserWorkspaceSchema.storage_access_key,
            UserWorkspaceSchema.storage_secret_key,
            UserWorkspaceSchema.storage_bucket,
            UserWorkspaceSchema.database_uri,
        )
        query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.owner_id == UserWorkspaceSchema.user_id,
        )
        query.where(
            UserAppletAccessSchema.applet_id == applet_id,
            UserWorkspaceSchema.use_arbitrary.is_(True),
        )
        query.limit(1)
        db_result = await self._execute(query)
        res = db_result.scalars().first()
        return res

    async def get_user_answers_db_info(
        self, user_id: uuid.UUID
    ) -> list[UserAnswersDBInfo]:
        query: Query = (
            select(
                UserAppletAccessSchema.applet_id,
                AppletSchema.encryption,
                UserWorkspaceSchema.use_arbitrary,
                UserWorkspaceSchema.database_uri,
            )
            .join(
                AppletSchema,
                AppletSchema.id == UserAppletAccessSchema.applet_id,
            )
            .outerjoin(
                UserWorkspaceSchema,
                UserWorkspaceSchema.user_id == UserAppletAccessSchema.owner_id,
            )
            .where(
                UserAppletAccessSchema.user_id == user_id,
                AppletSchema.soft_exists(),
                AppletSchema.encryption.isnot(None),
            )
            .order_by(
                UserWorkspaceSchema.use_arbitrary,
                UserWorkspaceSchema.database_uri,
            )
            .distinct()
        )
        db_result = await self._execute(query)

        res = db_result.all()

        return parse_obj_as(list[UserAnswersDBInfo], res)
