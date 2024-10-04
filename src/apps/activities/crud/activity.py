import uuid
from operator import and_
from typing import cast

from sqlalchemy import String, delete, func, literal, or_, select, text, union, update
from sqlalchemy.orm import Query, aliased

from apps.activities.db.schemas import ActivitySchema
from apps.activities.domain.activity import ActivityOrFlowBasicInfoInternal
from apps.activity_flows.db.schemas import ActivityFlowItemSchema, ActivityFlowSchema
from infrastructure.database import BaseCRUD

__all__ = ["ActivitiesCRUD"]


class ActivitiesCRUD(BaseCRUD[ActivitySchema]):
    schema_class = ActivitySchema

    async def update_by_id(self, id_, **values):
        query = update(self.schema_class)
        query = query.where(self.schema_class.id == id_)
        query = query.values(**values)
        query = query.returning(self.schema_class)
        await self._execute(query)

    async def create_many(
        self,
        activity_schemas: list[ActivitySchema],
    ) -> list[ActivitySchema]:
        instances = await self._create_many(activity_schemas)
        return instances

    async def delete_by_applet_id(self, applet_id: uuid.UUID):
        query = delete(ActivitySchema).where(ActivitySchema.applet_id == applet_id)
        await self._execute(query)

    async def get_by_applet_id(self, applet_id: uuid.UUID, is_reviewable=None) -> list[ActivitySchema]:
        query: Query = select(ActivitySchema)
        query = query.where(ActivitySchema.applet_id == applet_id)
        if isinstance(is_reviewable, bool):
            query = query.where(ActivitySchema.is_reviewable.is_(is_reviewable))
        query = query.order_by(ActivitySchema.order.asc())
        result = await self._execute(query)
        return result.scalars().all()

    async def get_mobile_with_items_by_applet_id(
        self,
        applet_id: uuid.UUID,
        is_reviewable=None,
    ) -> list:
        query: Query = select(
            ActivitySchema.id,
            ActivitySchema.name,
            ActivitySchema.description,
            ActivitySchema.splash_screen,
            ActivitySchema.image,
            ActivitySchema.show_all_at_once,
            ActivitySchema.is_skippable,
            ActivitySchema.is_reviewable,
            ActivitySchema.is_hidden,
            ActivitySchema.response_is_editable,
            ActivitySchema.order,
            ActivitySchema.scores_and_reports,
            ActivitySchema.performance_task_type,
            ActivitySchema.is_performance_task,
            ActivitySchema.auto_assign,
        )

        query = query.where(ActivitySchema.applet_id == applet_id)
        if isinstance(is_reviewable, bool):
            query = query.where(ActivitySchema.is_reviewable == is_reviewable)

        query = query.order_by(ActivitySchema.order.asc())
        result = await self._execute(query)

        return result.all()

    async def get_by_id(self, activity_id: uuid.UUID) -> ActivitySchema:
        activity = await self._get("id", activity_id)
        # TODO: Fix mypy for now. Later need to make get_by_id more consistant
        activity = cast(ActivitySchema, activity)
        return activity

    # Get by applet id and activity id
    async def get_by_applet_id_and_activity_id(self, applet_id: uuid.UUID, activity_id: uuid.UUID) -> ActivitySchema:
        query: Query = select(ActivitySchema)
        query = query.where(ActivitySchema.applet_id == applet_id)
        query = query.where(ActivitySchema.id == activity_id)

        result = await self._execute(query)
        return result.scalars().first()

    # get by applet id and activity ids
    async def get_by_applet_id_and_activities_ids(
        self, applet_id: uuid.UUID, activities_ids: list[uuid.UUID]
    ) -> list[ActivitySchema]:
        query: Query = select(ActivitySchema)
        query = query.where(ActivitySchema.applet_id == applet_id)
        query = query.where(ActivitySchema.id.in_(activities_ids))

        result = await self._execute(query)
        return result.scalars().all()

    async def get_ids_by_applet_id(self, applet_id: uuid.UUID) -> list[uuid.UUID]:
        query: Query = select(ActivitySchema.id)
        query = query.where(ActivitySchema.applet_id == applet_id)
        result = await self._execute(query)
        return result.scalars().all()

    async def get_activity_and_flow_basic_info_by_ids_or_auto(
        self, applet_id: uuid.UUID, ids: list[uuid.UUID], language: str
    ) -> list[ActivityOrFlowBasicInfoInternal]:
        activities_query: Query = select(
            ActivitySchema.id,
            ActivitySchema.name,
            ActivitySchema.description,
            ActivitySchema.image.label("images"),
            literal("").label("activity_ids"),
            literal(False).label("is_flow"),
            ActivitySchema.auto_assign,
            ActivitySchema.is_hidden,
            ActivitySchema.is_performance_task,
            ActivitySchema.performance_task_type,
            ActivitySchema.order,
        ).where(
            ActivitySchema.applet_id == applet_id,
            or_(
                ActivitySchema.id.in_(ids),
                ActivitySchema.auto_assign.is_(True),
            ),
        )

        flow_alias = aliased(ActivityFlowSchema)
        flow_items_alias = aliased(ActivityFlowItemSchema)
        activities_alias = aliased(ActivitySchema)

        flows_query = (
            select(
                flow_alias.id,
                flow_alias.name,
                flow_alias.description,
                func.coalesce(
                    func.string_agg(activities_alias.image, ",").filter(
                        and_(activities_alias.image.isnot(None), activities_alias.image != "")
                    ),
                    "",
                ).label("images"),
                func.string_agg(activities_alias.id.cast(String), ",").label("activity_ids"),
                literal(True).label("is_flow"),
                flow_alias.auto_assign,
                flow_alias.is_hidden,
                literal(None).label("is_performance_task"),
                literal(None).label("performance_task_type"),
                flow_alias.order,
            )
            .join(flow_items_alias, flow_alias.id == flow_items_alias.activity_flow_id)
            .join(activities_alias, flow_items_alias.activity_id == activities_alias.id)
            .where(
                flow_alias.applet_id == applet_id,
                or_(
                    flow_alias.id.in_(ids),
                    flow_alias.auto_assign.is_(True),
                ),
            )
            .group_by(flow_alias.id, flow_alias.name, flow_alias.description, flow_alias.auto_assign)
        )

        union_query = union(activities_query, flows_query).order_by(text("is_flow DESC"), text('"order" ASC'))

        result = await self.session.execute(union_query)
        return [
            ActivityOrFlowBasicInfoInternal(
                id=row[0],
                name=row[1],
                description=row[2][language],
                images=row[3].split(","),
                activity_ids=row[4].split(",") if row[4] else None,
                is_flow=row[5],
                auto_assign=row[6],
                is_hidden=row[7],
                is_performance_task=row[8],
                performance_task_type=row[9],
            )
            for row in result.fetchall()
        ]
