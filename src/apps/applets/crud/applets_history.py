import datetime
import uuid

from sqlalchemy import select, update
from sqlalchemy.orm import Query

from apps.applets.db.schemas import AppletHistorySchema
from apps.applets.domain.applet_create_update import AppletReportConfiguration
from apps.applets.errors import AppletVersionNotFoundError
from apps.users.db.schemas import UserSchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletHistoriesCRUD"]


class AppletHistoriesCRUD(BaseCRUD[AppletHistorySchema]):
    schema_class = AppletHistorySchema

    async def save(self, schema: AppletHistorySchema) -> AppletHistorySchema:
        return await self._create(schema)

    async def get_by_id_version(self, id_version: str) -> AppletHistorySchema | None:
        schema = await self._get("id_version", id_version)
        return schema

    async def retrieve_versions_by_applet_id(
        self, applet_id: uuid.UUID
    ) -> list[tuple[str, datetime.datetime, UserSchema]]:
        """
        Retrieve versions by applet id
        It will return version and user who made this version
        """
        query: Query = select(AppletHistorySchema, UserSchema)
        query = query.where(AppletHistorySchema.id == applet_id)
        query = query.join(
            UserSchema,
            UserSchema.id == AppletHistorySchema.user_id,
        )
        query = query.order_by(AppletHistorySchema.created_at.desc())
        result = await self._execute(query)
        results = result.all()
        return [
            (history_schema.version, history_schema.created_at, user_schema) for history_schema, user_schema in results
        ]

    async def retrieve_by_applet_version(self, id_version: str) -> AppletHistorySchema:
        history = await self.get_by_id_version(id_version)
        if history is None:
            raise AppletVersionNotFoundError()
        return history

    async def update_display_name(self, id_version: str, display_name: str):
        query: Query = update(AppletHistorySchema)
        query = query.where(AppletHistorySchema.id_version == id_version)
        query = query.values(
            display_name=display_name,
        )
        await self._execute(query)

    async def get_versions_by_applet_id(self, applet_id: uuid.UUID) -> list[str]:
        query: Query = select(AppletHistorySchema.version)
        query = query.where(AppletHistorySchema.id == applet_id)
        query = query.order_by(AppletHistorySchema.created_at.asc())
        result = await self._execute(query)
        return result.scalars().all()

    async def set_report_configuration(
        self,
        applet_id: uuid.UUID,
        version: str,
        schema: AppletReportConfiguration,
    ):
        query: Query = update(AppletHistorySchema)
        query = query.where(
            AppletHistorySchema.id_version == AppletHistorySchema.generate_id_version(applet_id, version)
        )
        query = query.values(**schema.dict(by_alias=False))

        await self._execute(query)

    async def get_current_versions_by_applet_id(self, applet_id: uuid.UUID) -> str:
        query: Query = select(AppletHistorySchema.id_version)
        query = query.where(AppletHistorySchema.id == applet_id)
        query = query.order_by(AppletHistorySchema.created_at.desc())
        query = query.limit(1)
        result = await self._execute(query)
        return result.scalars().first()
