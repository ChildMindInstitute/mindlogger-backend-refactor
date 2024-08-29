import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Query, aliased

from apps.activities.db.schemas import ActivitySchema
from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.shared.filtering import FilterField, Filtering
from apps.shared.query_params import QueryParams
from apps.subjects.db.schemas import SubjectSchema
from infrastructure.database import BaseCRUD

__all__ = ["ActivityAssigmentCRUD"]


class _ActivityAssignmentActivitiesFilter(Filtering):
    activities = FilterField(ActivitySchema.id, method_name="filter_by_activities_or_flows")

    def filter_by_activities_or_flows(self, field, values: list | str):
        if isinstance(values, str):
            values = values.split(",")

        if isinstance(values, list):
            values = list(filter(lambda x: x is not None, values))
            if values:
                return field.in_(values)


class _ActivityAssignmentFlowsFilter(Filtering):
    flows = FilterField(ActivityFlowSchema.id, method_name="filter_by_activities_or_flows")

    def filter_by_activities_or_flows(self, field, values: list | str):
        if isinstance(values, str):
            values = values.split(",")

        if isinstance(values, list):
            values = list(filter(lambda x: x is not None, values))
            if values:
                return field.in_(values)


class ActivityAssigmentCRUD(BaseCRUD[ActivityAssigmentSchema]):
    schema_class = ActivityAssigmentSchema

    async def create_many(self, schemas: list[ActivityAssigmentSchema]) -> list[ActivityAssigmentSchema]:
        return await self._create_many(schemas)

    async def already_exists(self, schema: ActivityAssigmentSchema) -> bool:
        query: Query = select(ActivityAssigmentSchema)
        query = query.where(ActivityAssigmentSchema.activity_id == schema.activity_id)
        query = query.where(ActivityAssigmentSchema.respondent_subject_id == schema.respondent_subject_id)
        query = query.where(ActivityAssigmentSchema.target_subject_id == schema.target_subject_id)
        query = query.where(ActivityAssigmentSchema.activity_flow_id == schema.activity_flow_id)
        query = query.where(ActivityAssigmentSchema.soft_exists())
        query = query.exists()
        db_result = await self._execute(select(query))
        return db_result.scalars().first() or False

    async def get_by_respondent_subject_id(self, respondent_subject_id) -> list[ActivityAssigmentSchema]:
        query: Query = select(ActivityAssigmentSchema)
        query = query.where(ActivityAssigmentSchema.respondent_subject_id == respondent_subject_id)
        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_by_applet(self, applet_id: uuid.UUID, query_params: QueryParams) -> list[ActivityAssigmentSchema]:
        respondent_schema = aliased(SubjectSchema)
        target_schema = aliased(SubjectSchema)

        query = (
            select(ActivityAssigmentSchema)
            .outerjoin(ActivitySchema, ActivitySchema.id == ActivityAssigmentSchema.activity_id)
            .outerjoin(ActivityFlowSchema, ActivityFlowSchema.id == ActivityAssigmentSchema.activity_flow_id)
            .join(respondent_schema, respondent_schema.id == ActivityAssigmentSchema.respondent_subject_id)
            .join(target_schema, target_schema.id == ActivityAssigmentSchema.target_subject_id)
            .where(
                or_(
                    ActivityFlowSchema.applet_id == applet_id,
                    ActivitySchema.applet_id == applet_id,
                ),
                ActivityAssigmentSchema.soft_exists(),
                respondent_schema.soft_exists(),
                target_schema.soft_exists(),
            )
        )
        if query_params.filters:
            activities_clause = _ActivityAssignmentActivitiesFilter().get_clauses(**query_params.filters)
            flows_clause = _ActivityAssignmentFlowsFilter().get_clauses(**query_params.filters)

            query = query.where(or_(*activities_clause, *flows_clause))

        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_by_applet_and_respondent(
        self, applet_id: uuid.UUID, respondent_subject_id: uuid.UUID
    ) -> list[ActivityAssigmentSchema]:
        respondent_schema = aliased(SubjectSchema)
        target_schema = aliased(SubjectSchema)
        query = (
            select(ActivityAssigmentSchema)
            .outerjoin(ActivitySchema, ActivitySchema.id == ActivityAssigmentSchema.activity_id)
            .outerjoin(ActivityFlowSchema, ActivityFlowSchema.id == ActivityAssigmentSchema.activity_flow_id)
            .join(respondent_schema, respondent_schema.id == ActivityAssigmentSchema.respondent_subject_id)
            .join(target_schema, target_schema.id == ActivityAssigmentSchema.target_subject_id)
            .where(
                or_(
                    ActivityFlowSchema.applet_id == applet_id,
                    ActivitySchema.applet_id == applet_id,
                ),
                ActivityAssigmentSchema.soft_exists(),
                respondent_schema.soft_exists(),
                target_schema.soft_exists(),
                respondent_schema.id == respondent_subject_id,
            )
        )

        db_result = await self._execute(query)

        return db_result.scalars().all()
