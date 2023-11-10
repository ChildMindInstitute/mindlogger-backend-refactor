import datetime
import uuid

from sqlalchemy import select, update
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Query

from apps.applets import errors
from apps.applets.db.schemas import AppletHistorySchema
from apps.applets.domain.applet_create_update import AppletReportConfiguration
from apps.applets.errors import AppletVersionNotFoundError
from apps.users.db.schemas import UserSchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletHistoriesCRUD"]


class AppletHistoriesCRUD(BaseCRUD[AppletHistorySchema]):
    schema_class = AppletHistorySchema

    async def save(self, schema: AppletHistorySchema):
        await self._create(schema)

    async def get_by_id_version(
        self, id_version: str
    ) -> AppletHistorySchema | None:
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
            (history_schema.version, history_schema.created_at, user_schema)
            for history_schema, user_schema in results
        ]

    async def retrieve_by_applet_version(
        self, id_version: str
    ) -> AppletHistorySchema:
        query: Query = select(AppletHistorySchema)
        query = query.where(AppletHistorySchema.id_version == id_version)
        result = await self._execute(query)
        try:
            return result.scalars().one()
        except NoResultFound:
            raise AppletVersionNotFoundError()

    async def fetch_by_id_version(self, value: str) -> AppletHistorySchema:
        schema = await self._get("id_version", value)
        if not schema:
            raise errors.AppletNotFoundError(
                key="id_version",
                value=value,
            )
        return schema

    async def update_display_name(self, id_version: str, display_name: str):
        query: Query = update(AppletHistorySchema)
        query = query.where(AppletHistorySchema.id_version == id_version)
        query = query.values(
            display_name=display_name,
        )
        await self._execute(query)

    async def get_id_versions_by_applet_id(
        self, applet_id: uuid.UUID
    ) -> list[str]:
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
            AppletHistorySchema.id_version
            == AppletHistorySchema.generate_id_version(applet_id, version)
        )
        query = query.values(**schema.dict(by_alias=False))

        await self._execute(query)
