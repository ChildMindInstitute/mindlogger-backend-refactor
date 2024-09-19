import uuid
from typing import cast

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivitySchema
from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from apps.activity_flows.db.schemas import ActivityFlowSchema
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

    async def get_assigned_activity_and_flows(
        self, applet_id: uuid.UUID, target_subject_id: uuid.UUID
    ) -> list[
        ActivityOrFlowWithAssignmentsPublic
    ]:  # TODO: Change this to a InternalModel class, check if already exist a class that fits
        # TODO: Write this query joining ActivityAssigmentSchema, ActivityFlowSchema and ActivitySchema
        # TODO: Pay attention to images field, we should use aggregate function to get all images for each flow
        # TODO: In case of an activity, this images array, should return only one image

        # TODO: check the methods UserAppletAccessCRUD.get_workspace_managers() and UserAppletAccessCRUD.get_workspace_respondents() as examples of complex queries with aggregations and CTE
        query: Query = (
            select(
                ActivitySchema.id.label("activity_id"),
                ActivitySchema.name.label("activity_name"),
                ActivitySchema.description.label("activity_description"),
                ActivityAssigmentSchema,
                ActivityFlowSchema,
            )
            .join(ActivityAssigmentSchema, ActivitySchema.id == ActivityAssigmentSchema.activity_id)
            .join(ActivityFlowSchema, ActivityFlowSchema.id == ActivityAssigmentSchema.activity_flow_id)
            .where(ActivitySchema.applet_id == applet_id)
            .where(ActivityAssigmentSchema.target_subject_id == target_subject_id)
            .order_by(ActivityFlowSchema.order.asc(), ActivitySchema.order.asc())
        )
        result = await self._execute(query)
        return result.scalars().all()
