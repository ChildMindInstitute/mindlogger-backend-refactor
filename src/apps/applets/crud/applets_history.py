from sqlalchemy import select
from sqlalchemy.orm import Query, joinedload

from apps.activities.crud import ActivitiesHistoryCRUD
from apps.activity_flows.crud import FlowsHistoryCRUD
from apps.applets import errors
from apps.applets.db.schemas import AppletHistorySchema
from apps.applets.domain import History, detailing_history
from apps.users.db.schemas import UserSchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["AppletHistoryCRUD"]


class AppletHistoryCRUD(BaseCRUD[AppletHistorySchema]):
    schema_class = AppletHistorySchema
    initial_version = "1.0.0"
    version_difference = 0.01

    async def save(self, schema: AppletHistorySchema):
        await self._create(schema)

    async def histories_by_applet_id(self, applet_id: int) -> list[History]:
        query: Query = select(AppletHistorySchema)
        query = query.execution_options(populate_existing=True)
        query = query.where(AppletHistorySchema.id == applet_id)
        query = query.join(
            UserSchema,
            UserSchema.id == AppletHistorySchema.creator_id,
        )
        query = query.options(
            joinedload(AppletHistorySchema.creator),
        )
        query = query.order_by(AppletHistorySchema.created_at.desc())
        result = await self._execute(query)
        results = result.scalars().all()
        histories = []

        for result in results:
            histories.append(History.from_orm(result))
        return histories

    async def get_full(self, applet_id: int, version: str):
        applet_id_version = f"{applet_id}_{version}"
        instance = await self._fetch(applet_id_version)
        applet = detailing_history.Applet.from_orm(instance)
        applet.activities, activities_map = await ActivitiesHistoryCRUD().list(
            applet_id_version
        )
        applet.activity_flows = await FlowsHistoryCRUD().list(
            applet_id_version, activities_map
        )
        return applet

    async def _fetch(self, applet_id_version: str) -> AppletHistorySchema:
        if not (instance := await self._get("id_version", applet_id_version)):
            raise errors.AppletNotFoundError(
                "No such applet's history "
                f"with id_version={applet_id_version}."
            )

        return instance
