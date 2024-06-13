import uuid

from pydantic import parse_obj_as
from sqlalchemy import any_, func, select
from sqlalchemy.orm import Query, joinedload
from sqlalchemy.sql.operators import is_

from apps.activities.db.schemas import ActivityHistorySchema
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema, ActivityFlowItemHistorySchema
from apps.activity_flows.domain.flow_full import FlowHistoryWithActivityFull
from apps.applets.db.schemas import AppletHistorySchema
from apps.applets.domain.applet_history import Version
from infrastructure.database import BaseCRUD

__all__ = ["FlowsHistoryCRUD"]


class FlowsHistoryCRUD(BaseCRUD[ActivityFlowHistoriesSchema]):
    schema_class = ActivityFlowHistoriesSchema

    async def create_many(
        self,
        flows: list[ActivityFlowHistoriesSchema],
    ):
        await self._create_many(flows)

    async def retrieve_by_applet_version(self, id_version: str) -> list[ActivityFlowHistoriesSchema]:
        query: Query = select(ActivityFlowHistoriesSchema)
        query = query.where(ActivityFlowHistoriesSchema.applet_id == id_version)
        query = query.order_by(ActivityFlowHistoriesSchema.order.asc())
        result = await self._execute(query)
        return result.scalars().all()

    async def get_by_id_versions(self, id_versions: list[str]) -> list[ActivityFlowHistoriesSchema]:
        if not id_versions:
            return []

        query: Query = select(ActivityFlowHistoriesSchema)
        query = query.where(ActivityFlowHistoriesSchema.id_version == any_(id_versions))
        result = await self._execute(query)
        return result.scalars().all()

    async def load_full(self, id_versions: list[str]) -> list[FlowHistoryWithActivityFull]:
        if not id_versions:
            return []

        query = (
            select(ActivityFlowHistoriesSchema)
            .options(
                joinedload(ActivityFlowHistoriesSchema.items, innerjoin=True)
                .joinedload(ActivityFlowItemHistorySchema.activity, innerjoin=True)
                .joinedload(ActivityHistorySchema.items, innerjoin=True)
            )
            .where(ActivityFlowHistoriesSchema.id_version.in_(id_versions))
        )
        res = await self._execute(query)
        data = res.unique().scalars().all()

        return parse_obj_as(list[FlowHistoryWithActivityFull], data)

    async def get_by_applet_id(self, applet_id: str) -> list[ActivityFlowHistoriesSchema]:
        query: Query = select(ActivityFlowHistoriesSchema)
        query = query.where(ActivityFlowHistoriesSchema.applet_id == applet_id)
        query = query.order_by(ActivityFlowHistoriesSchema.order.asc())
        result = await self._execute(query)
        return result.scalars().all()

    async def retrieve_by_applet_ids(self, applet_versions: list[str]) -> list[ActivityFlowHistoriesSchema]:
        """
        retrieve flows by applet id_version fields
        order by id
        """
        query: Query = select(ActivityFlowHistoriesSchema)
        query = query.join(
            AppletHistorySchema,
            AppletHistorySchema.id_version == ActivityFlowHistoriesSchema.applet_id,
        )
        query = query.where(AppletHistorySchema.id_version.in_(applet_versions))
        query = query.order_by(
            ActivityFlowHistoriesSchema.id.asc(),
            ActivityFlowHistoriesSchema.updated_at.asc(),
        )
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_last_histories_by_applet(self, applet_id: uuid.UUID) -> list[ActivityFlowHistoriesSchema]:
        """
        Get last versions including deleted from the applet
        """
        query: Query = select(ActivityFlowHistoriesSchema)
        query = query.join(
            AppletHistorySchema,
            AppletHistorySchema.id_version == ActivityFlowHistoriesSchema.applet_id,
        )
        query = query.where(AppletHistorySchema.id == applet_id)
        query = query.order_by(
            ActivityFlowHistoriesSchema.id.desc(),
            ActivityFlowHistoriesSchema.created_at.desc(),
        )
        query = query.distinct(ActivityFlowHistoriesSchema.id)
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_versions_data(self, flow_id: uuid.UUID) -> list[Version]:
        query: Query = (
            select(
                AppletHistorySchema.version,
                AppletHistorySchema.created_at,
            )
            .select_from(ActivityFlowHistoriesSchema)
            .join(AppletHistorySchema, AppletHistorySchema.id_version == ActivityFlowHistoriesSchema.applet_id)
            .where(ActivityFlowHistoriesSchema.id == flow_id)
            .order_by(AppletHistorySchema.created_at)
        )
        result = await self._execute(query)
        data = result.all()

        return parse_obj_as(list[Version], data)

    async def get_list_by_id(self, id_: uuid.UUID) -> list[ActivityFlowHistoriesSchema]:
        query: Query = select(ActivityFlowHistoriesSchema)
        query = query.where(ActivityFlowHistoriesSchema.id == id_)
        result = await self._execute(query)
        return result.scalars().all()

    async def reduce_flow_versions_to_performance_flow_ids(self, id_versions: list[str]) -> list[uuid.UUID]:
        """
        Get flow ids with the list of all activities of performance type for flow versions
        """
        query: Query = (
            select(ActivityFlowHistoriesSchema.id)
            .join(ActivityFlowHistoriesSchema.items)
            .join(ActivityFlowItemHistorySchema.activity)
            .where(
                ActivityFlowHistoriesSchema.id_version.in_(id_versions),
                ActivityHistorySchema.is_reviewable.isnot(True),
            )
            .group_by(ActivityFlowHistoriesSchema.id)
            .having(func.bool_and(is_(ActivityHistorySchema.is_performance_task, True)))
        )
        result = await self._execute(query)
        return result.scalars().all()
