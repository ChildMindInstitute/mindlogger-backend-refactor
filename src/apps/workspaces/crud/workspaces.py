import uuid

from pydantic import parse_obj_as
from sqlalchemy import and_, select
from sqlalchemy.engine import Result
from sqlalchemy.orm import Query

from apps.applets.db.schemas import AppletSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema, UserWorkspaceSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.workspace import UserAnswersDBInfo
from infrastructure.database.crud import BaseCRUD

__all__ = ["UserWorkspaceCRUD"]


class UserWorkspaceCRUD(BaseCRUD[UserWorkspaceSchema]):
    schema_class = UserWorkspaceSchema

    async def get_by_user_id(self, user_id_: uuid.UUID) -> UserWorkspaceSchema:
        query: Query = select(self.schema_class).filter(self.schema_class.user_id == user_id_)
        result: Result = await self._execute(query)

        return result.scalars().one_or_none()

    async def get_by_ids(self, ids: list[uuid.UUID]) -> list[UserWorkspaceSchema]:
        query: Query = select(self.schema_class)
        query = query.filter(self.schema_class.user_id.in_(ids))
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_all(self) -> list[UserWorkspaceSchema]:
        return await self._all()

    async def save(self, schema: UserWorkspaceSchema) -> UserWorkspaceSchema:
        """Return UserWorkspace instance."""
        return await self._create(schema)

    async def update_by_user_id(self, user_id: uuid.UUID, schema: UserWorkspaceSchema) -> UserWorkspaceSchema:
        instance = await self._update_one(
            lookup="user_id",
            value=user_id,
            schema=schema,
        )
        return instance

    async def get_by_applet_id(self, applet_id: uuid.UUID) -> UserWorkspaceSchema | None:
        access_subquery: Query = select(UserAppletAccessSchema.owner_id)
        access_subquery = access_subquery.where(
            and_(
                UserAppletAccessSchema.role == Role.OWNER,
                UserAppletAccessSchema.applet_id == applet_id,
                UserAppletAccessSchema.is_deleted.is_(False),
            )
        )
        query: Query = select(UserWorkspaceSchema)
        query = query.where(UserWorkspaceSchema.user_id.in_(access_subquery))
        db_result = await self._execute(query)
        res = db_result.scalars().first()
        return res

    async def get_arbitraries_map_by_applet_ids(self, applet_ids: list[uuid.UUID]) -> dict[str | None, list[uuid.UUID]]:
        """Returning map {"arbitrary_uri": [applet_ids]}"""
        applet_owner_map = await self._get_applet_owners_map_by_applet_ids(applet_ids)
        owner_ids = set(applet_owner_map.values())

        query: Query = select(UserWorkspaceSchema)
        query = query.where(UserWorkspaceSchema.user_id.in_(owner_ids))
        db_result = await self._execute(query)
        res = db_result.scalars().all()

        user_arb_uri_map: dict[uuid.UUID, str] = dict()
        for user_workspace in res:
            user_arb_uri_map[user_workspace.user_id] = (
                user_workspace.database_uri if user_workspace.use_arbitrary else None
            )

        arb_uri_applet_ids_map: dict[str | None, list[uuid.UUID]] = dict()
        for applet_id in applet_ids:
            user_id = applet_owner_map[applet_id]
            arb_uri = user_arb_uri_map[user_id]
            arb_uri_applet_ids_map.setdefault(arb_uri, list())
            arb_uri_applet_ids_map[arb_uri].append(applet_id)

        return arb_uri_applet_ids_map

    async def _get_applet_owners_map_by_applet_ids(self, applet_ids: list[uuid.UUID]) -> dict[uuid.UUID, uuid.UUID]:
        """Returning map {"applet_id": owner_id(user_id)}"""
        query: Query = select(UserAppletAccessSchema)
        query = query.where(
            and_(
                UserAppletAccessSchema.role == Role.OWNER,
                UserAppletAccessSchema.applet_id.in_(applet_ids),
            )
        )
        db_result = await self._execute(query)
        res = db_result.scalars().all()

        applet_owner_map: dict[uuid.UUID, uuid.UUID] = dict()
        for user_applet_access in res:
            applet_owner_map[user_applet_access.applet_id] = user_applet_access.owner_id

        return applet_owner_map

    async def get_user_answers_db_info(self, user_id: uuid.UUID) -> list[UserAnswersDBInfo]:
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

    async def get_arbitrary_list(self) -> UserWorkspaceSchema:
        query: Query = select(UserWorkspaceSchema)
        query = query.where(UserWorkspaceSchema.database_uri.isnot(None))
        result: Result = await self._execute(query)
        return result.scalars().all()
