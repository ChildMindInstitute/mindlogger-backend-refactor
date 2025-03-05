import uuid

from pydantic import parse_obj_as
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivityHistorySchema
from apps.activity_flows.db.schemas import ActivityFlowHistoriesSchema, ActivityFlowItemHistorySchema
from apps.activity_flows.domain.flow_full import FlowItemHistoryFull
from apps.applets.db.schemas import AppletHistorySchema
from apps.applets.domain.applet_history import FlowItemHistoryDto
from apps.shared.filtering import Filtering, FilterField, Comparisons
from apps.shared.query_params import QueryParams
from infrastructure.database import BaseCRUD

__all__ = ["FlowItemHistoriesCRUD"]


class _FlowItemHistoryFilters(Filtering):
    from_date = FilterField(ActivityFlowItemHistorySchema.created_at, Comparisons.GREAT_OR_EQUAL)
    to_date = FilterField(ActivityFlowItemHistorySchema.created_at, Comparisons.LESS_OR_EQUAL)


class FlowItemHistoriesCRUD(BaseCRUD[ActivityFlowItemHistorySchema]):
    schema_class = ActivityFlowItemHistorySchema

    async def create_many(
        self,
        items: list[ActivityFlowItemHistorySchema],
    ):
        await self._create_many(items)

    async def retrieve_by_applet_version(self, id_version: str) -> list[ActivityFlowItemHistorySchema]:
        query: Query = select(ActivityFlowItemHistorySchema)
        query = query.join(
            ActivityFlowHistoriesSchema,
            ActivityFlowHistoriesSchema.id_version == ActivityFlowItemHistorySchema.activity_flow_id,
        )
        query = query.where(ActivityFlowHistoriesSchema.applet_id == id_version)
        query = query.order_by(
            ActivityFlowItemHistorySchema.order.asc(),
        )
        result = await self._execute(query)
        return result.scalars().all()

    async def get_by_flow_id(self, flow_id: str) -> list[ActivityFlowItemHistorySchema]:
        query: Query = select(ActivityFlowItemHistorySchema)
        query = query.where(ActivityFlowItemHistorySchema.activity_flow_id == flow_id)
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_flow_ids(self, flow_ids: list[str]) -> list[ActivityFlowItemHistorySchema]:
        query: Query = select(ActivityFlowItemHistorySchema)
        query = query.where(ActivityFlowItemHistorySchema.activity_flow_id.in_(flow_ids))
        query = query.order_by(ActivityFlowItemHistorySchema.order.asc())
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_map(self, activity_flow_map: dict[str, str]) -> list[ActivityFlowItemHistorySchema]:
        query: Query = select(ActivityFlowItemHistorySchema)
        filters = []
        for activity_id, flow_id in activity_flow_map.items():
            filters.append(
                and_(
                    ActivityFlowItemHistorySchema.activity_id == activity_id,
                    ActivityFlowItemHistorySchema.activity_flow_id == flow_id,
                )
            )

        query = query.where(or_(*filters))
        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_by_flow_id_versions(self, id_versions: list[str]) -> list[FlowItemHistoryFull]:
        query: Query = select(
            ActivityFlowItemHistorySchema.id,
            ActivityFlowItemHistorySchema.activity_flow_id,
            ActivityFlowItemHistorySchema.activity_id,
            ActivityFlowItemHistorySchema.id_version,
            ActivityFlowItemHistorySchema.order,
            ActivityHistorySchema.name,
        )
        query = query.join(
            ActivityHistorySchema,
            ActivityHistorySchema.id_version == ActivityFlowItemHistorySchema.activity_id,
        )
        query = query.where(ActivityFlowItemHistorySchema.activity_flow_id.in_(id_versions))
        query = query.order_by(ActivityFlowItemHistorySchema.order.asc())
        db_result = await self._execute(query)
        res = db_result.all()
        return [parse_obj_as(FlowItemHistoryFull, row) for row in res]

    async def get_flow_item_history_by_applet(
        self, applet_id: uuid.UUID, query_params: QueryParams
    ) -> tuple[list[FlowItemHistoryDto], int]:
        query: Query = select(
            AppletHistorySchema.id.label('applet_id'),
            AppletHistorySchema.version.label('applet_version'),
            AppletHistorySchema.display_name.label('applet_name'),
            ActivityFlowHistoriesSchema.id.label('flow_id'),
            ActivityFlowHistoriesSchema.name.label('flow_name'),
            ActivityHistorySchema.id.label('activity_id'),
            ActivityHistorySchema.name.label('activity_name'),
            ActivityFlowItemHistorySchema.created_at,
        )

        query = query.select_from(ActivityFlowItemHistorySchema)
        query = query.join(
            ActivityFlowHistoriesSchema,
            ActivityFlowHistoriesSchema.id_version == ActivityFlowItemHistorySchema.activity_flow_id,
        )
        query = query.join(
            ActivityHistorySchema,
            ActivityFlowItemHistorySchema.activity_id == ActivityHistorySchema.id_version,
        )
        query = query.join(
            AppletHistorySchema,
            and_(
                AppletHistorySchema.id_version == ActivityFlowHistoriesSchema.applet_id,
                AppletHistorySchema.id_version == ActivityHistorySchema.applet_id,
            )
        )

        query = query.where(AppletHistorySchema.id == applet_id)

        _filters = _FlowItemHistoryFilters().get_clauses(**query_params.filters)
        if _filters:
            query = query.where(*_filters)

        query = query.order_by(
            ActivityFlowItemHistorySchema.created_at,
            AppletHistorySchema.id,
            ActivityFlowHistoriesSchema.id,
            ActivityHistorySchema.id,
        )

        db_result = await self._execute(query)

        # TODO: Implement pagination
        return [FlowItemHistoryDto(**row) for row in db_result], 0
