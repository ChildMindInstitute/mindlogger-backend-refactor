import datetime

from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.applets import errors
from apps.applets.db.schemas import AppletHistorySchema
from apps.users.db.schemas import UserSchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletHistoriesCRUD"]


class AppletHistoriesCRUD(BaseCRUD[AppletHistorySchema]):
    schema_class = AppletHistorySchema

    async def save(self, schema: AppletHistorySchema):
        await self._create(schema)

    async def retrieve_versions_by_applet_id(
        self, applet_id: int
    ) -> list[tuple[str, datetime.datetime, UserSchema]]:
        """
        Retrieve versions by applet id
        It will return version and user who made this version
        """
        query: Query = select(AppletHistorySchema, UserSchema)
        query = query.execution_options(populate_existing=True)
        query = query.where(AppletHistorySchema.id == applet_id)
        query = query.join(
            UserSchema,
            UserSchema.id == AppletHistorySchema.creator_id,
        )
        query = query.order_by(AppletHistorySchema.created_at.desc())
        result = await self._execute(query)
        results = result.all()
        return [
            (history_schema.version, history_schema.created_at, user_schema)
            for history_schema, user_schema in results
        ]

    async def retrieve_by_applet_version(
        self, id_version: str
    ) -> AppletHistorySchema | None:
        query: Query = select(AppletHistorySchema)
        query = query.where(AppletHistorySchema.id_version == id_version)
        result = await self._execute(query)
        return result.scalars().one_or_none()

    async def _fetch(self, applet_id_version: str) -> AppletHistorySchema:
        if not (instance := await self._get("id_version", applet_id_version)):
            raise errors.AppletNotFoundError(
                key="id_version",
                value=applet_id_version,
            )

        return instance

    async def fetch_by_id_version(self, value: str) -> AppletHistorySchema:
        schema = await self._get("id_version", value)
        if not schema:
            raise
        return schema
