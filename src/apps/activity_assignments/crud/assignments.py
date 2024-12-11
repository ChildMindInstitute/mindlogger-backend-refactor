import datetime
import uuid

from sqlalchemy import and_, case, func, or_, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import InstrumentedAttribute, Query, aliased

from apps.activities.db.schemas import ActivitySchema
from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from apps.activity_assignments.domain.assignments import ActivityAssignmentCreate
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


class _ActivityAssignmentSubjectFilter(Filtering):
    respondent_subject_id = FilterField(ActivityAssigmentSchema.respondent_subject_id)
    target_subject_id = FilterField(ActivityAssigmentSchema.target_subject_id)


class ActivityAssigmentCRUD(BaseCRUD[ActivityAssigmentSchema]):
    schema_class = ActivityAssigmentSchema

    async def create_many(self, schemas: list[ActivityAssigmentSchema]) -> list[ActivityAssigmentSchema]:
        """
        Creates multiple activity assignment records in the database.

        This method utilizes the `_create_many` method from the `BaseCRUD` class to insert
        multiple `ActivityAssigmentSchema` records into the database in a single operation.

        Parameters:
        -----------
        schemas : list[ActivityAssigmentSchema]
            A list of activity assignment schemas to be created.

        Returns:
        --------
        list[ActivityAssigmentSchema]
            A list of the created `ActivityAssigmentSchema` objects.

        Notes:
        ------
        - Inherits functionality from `BaseCRUD`, which provides the `_create_many` method for
        bulk insertion operations.
        - Ensures that all new assignments are created in a single database transaction.
        """
        if len(schemas) == 0:
            return []

        return await self._create_many(schemas)

    async def exist(self, assignment: ActivityAssignmentCreate) -> ActivityAssigmentSchema | None:
        """
        Checks if an activity assignment exists in the database.

        This method builds a query to check for the existence of an assignment with the same
        `activity_id`, `activity_flow_id`, `respondent_subject_id`, and `target_subject_id`,
        while ensuring the record has not been soft-deleted.

        Parameters:
        -----------
        assignment : ActivityAssignmentCreate
            The activity assignment schema to check for existence.

        Returns:
        --------
        ActivityAssigmentSchema | None
            The value of the first matching record, if it exists. Otherwise, returns None.

        Notes:
        ------
        - The existence check excludes soft-deleted records.
        """
        query: Query = select(ActivityAssigmentSchema)
        query = query.where(
            ActivityAssigmentSchema.activity_id == assignment.activity_id,
            ActivityAssigmentSchema.activity_flow_id == assignment.activity_flow_id,
            ActivityAssigmentSchema.respondent_subject_id == assignment.respondent_subject_id,
            ActivityAssigmentSchema.target_subject_id == assignment.target_subject_id,
            ActivityAssigmentSchema.soft_exists(),
        )

        db_result = await self._execute(query)
        return db_result.scalars().one_or_none()

    async def get_target_subject_ids_by_activity_or_flow_ids(
        self,
        respondent_subject_id: uuid.UUID,
        activity_or_flow_ids: list[uuid.UUID] = [],
    ) -> list[uuid.UUID]:
        """
        Retrieves the IDs of target subjects that have assignments to be completed by the provided respondent.

        Parameters:
        ----------
        respondent_subject_id : uuid.UUID
            The ID of the respondent subject to search for. This parameter is required.
        activity_or_flow_ids : list[uuid.UUID]
            Optional list of activity or flow IDs to narrow the search. These IDs may correspond to either
            `activity_id` or `activity_flow_id` fields

        Returns:
        -------
        list[uuid.UUID]
            List of target subject IDs associated with the provided activity or flow IDs.
        """
        query = select(ActivityAssigmentSchema.target_subject_id).where(
            ActivityAssigmentSchema.respondent_subject_id == respondent_subject_id,
            ActivityAssigmentSchema.soft_exists(),
        )

        if len(activity_or_flow_ids) > 0:
            query = query.where(
                or_(
                    ActivityAssigmentSchema.activity_id.in_(activity_or_flow_ids),
                    ActivityAssigmentSchema.activity_flow_id.in_(activity_or_flow_ids),
                )
            )

        db_result = await self._execute(query.distinct())

        return db_result.scalars().all()

    async def delete_by_activity_or_flow_ids(self, activity_or_flow_ids: list[uuid.UUID]):
        """
        Marks the `is_deleted` field as True for all matching assignments based on the provided
        activity or flow IDs. The method ensures that each ID corresponds to a unique record by
        treating the ID as a unique combination.

        Parameters:
        ----------
        activity_or_flow_ids : list[uuid.UUID]
            List of activity or flow IDs to search for. These IDs may correspond to either
            `activity_id` or `activity_flow_id` fields.

        Returns:
        -------
        None

        Raises:
        ------
        AssertionError
            If the provided ID list is empty.
        """
        assert len(activity_or_flow_ids) > 0

        stmt = (
            update(ActivityAssigmentSchema)
            .where(
                or_(
                    ActivityAssigmentSchema.activity_id.in_(activity_or_flow_ids),
                    ActivityAssigmentSchema.activity_flow_id.in_(activity_or_flow_ids),
                )
            )
            .values(is_deleted=True)
        )
        await self._execute(stmt)

    async def delete_many(
        self,
        activity_or_flow_ids: list[uuid.UUID],
        respondent_subject_ids: list[uuid.UUID],
        target_subject_ids: list[uuid.UUID],
    ):
        """
        Marks the `is_deleted` field as True for all matching assignments based on the provided
        activity or flow IDs, respondent subject IDs, and target subject IDs. The method ensures
        that each set of IDs corresponds to a unique record by treating the IDs in a tuple
        (activity/flow ID, respondent subject ID, target subject ID) as a unique combination.

        Parameters:
        ----------
        activity_or_flow_ids : list[uuid.UUID]
            List of activity or flow IDs to search for. These IDs may correspond to either
            `activity_id` or `activity_flow_id` fields.
        respondent_subject_ids : list[uuid.UUID]
            List of respondent subject IDs to match against.
        target_subject_ids : list[uuid.UUID]
            List of target subject IDs to match against.

        Returns:
        -------
        None

        Raises:
        ------
        AssertionError
            If the lengths of the provided ID lists do not match.
        """
        # Ensure all lists are of equal length
        assert len(activity_or_flow_ids) == len(respondent_subject_ids) == len(target_subject_ids)

        stmt = (
            update(ActivityAssigmentSchema)
            .where(
                or_(
                    tuple_(
                        ActivityAssigmentSchema.activity_id,
                        ActivityAssigmentSchema.respondent_subject_id,
                        ActivityAssigmentSchema.target_subject_id,
                    ).in_(zip(activity_or_flow_ids, respondent_subject_ids, target_subject_ids)),
                    tuple_(
                        ActivityAssigmentSchema.activity_flow_id,
                        ActivityAssigmentSchema.respondent_subject_id,
                        ActivityAssigmentSchema.target_subject_id,
                    ).in_(zip(activity_or_flow_ids, respondent_subject_ids, target_subject_ids)),
                )
            )
            .values(is_deleted=True)
        )
        await self._execute(stmt)

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
                or_(ActivityFlowSchema.applet_id == applet_id, ActivitySchema.applet_id == applet_id),
                ActivityAssigmentSchema.soft_exists(),
                respondent_schema.soft_exists(),
                target_schema.soft_exists(),
            )
        )
        if query_params.filters:
            activities_clause = _ActivityAssignmentActivitiesFilter().get_clauses(**query_params.filters)
            flows_clause = _ActivityAssignmentFlowsFilter().get_clauses(**query_params.filters)
            subject_clauses = _ActivityAssignmentSubjectFilter().get_clauses(**query_params.filters)

            query = query.where(
                and_(
                    or_(*activities_clause, *flows_clause)
                    if len(activities_clause) > 0 or len(flows_clause) > 0
                    else True,
                    or_(*subject_clauses) if len(subject_clauses) > 0 else True,
                )
            )

        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def upsert(self, values: dict) -> ActivityAssigmentSchema | None:
        stmt = (
            insert(ActivityAssigmentSchema)
            .values(values)
            .on_conflict_do_update(
                index_elements=[
                    ActivityAssigmentSchema.respondent_subject_id,
                    ActivityAssigmentSchema.target_subject_id,
                    ActivityAssigmentSchema.activity_id
                    if values.get("activity_id")
                    else ActivityAssigmentSchema.activity_flow_id,
                ],
                set_={
                    "updated_at": datetime.datetime.utcnow(),
                    "is_deleted": False,
                },
                where=(ActivityAssigmentSchema.soft_exists(exists=False)),
            )
            .returning(ActivityAssigmentSchema.id)
        )

        result = await self._execute(stmt)
        model_id = result.scalar_one_or_none()
        updated_schema = None
        if model_id:
            updated_schema = await self._get("id", model_id)

        return updated_schema

    async def check_if_auto_assigned(self, activity_or_flow_id: uuid.UUID) -> bool | None:
        """
        Checks if the activity or flow is currently set to auto-assign.
        """
        activities_query = select(ActivitySchema.auto_assign).where(ActivitySchema.id == activity_or_flow_id)
        flows_query = select(ActivityFlowSchema.auto_assign).where(ActivityFlowSchema.id == activity_or_flow_id)

        union_query = activities_query.union_all(flows_query).limit(1)

        db_result = await self._execute(union_query)
        return db_result.scalar_one_or_none()

    @staticmethod
    def _activity_and_flow_ids_by_subject_query(subject_column: InstrumentedAttribute, subject_id: uuid.UUID) -> Query:
        respondent_schema = aliased(SubjectSchema)
        target_schema = aliased(SubjectSchema)

        query: Query = (
            select(
                case(
                    (
                        ActivityAssigmentSchema.activity_id.isnot(None),
                        ActivityAssigmentSchema.activity_id,
                    ),
                    else_=ActivityAssigmentSchema.activity_flow_id,
                ).label("activity_id"),
                func.array_agg(
                    ActivityAssigmentSchema.respondent_subject_id
                    if subject_column == ActivityAssigmentSchema.target_subject_id
                    else ActivityAssigmentSchema.target_subject_id
                ).label("subject_ids"),
                func.count(ActivityAssigmentSchema.id).label("assignments_count"),
            )
            .join(respondent_schema, respondent_schema.id == ActivityAssigmentSchema.respondent_subject_id)
            .join(target_schema, target_schema.id == ActivityAssigmentSchema.target_subject_id)
            .where(
                subject_column == subject_id,
                ActivityAssigmentSchema.soft_exists(),
                respondent_schema.soft_exists(),
                target_schema.soft_exists(),
            )
            .group_by("activity_id", ActivityAssigmentSchema.activity_id, ActivityAssigmentSchema.activity_flow_id)
        )

        return query

    async def get_assignments_by_target_subject(self, target_subject_id: uuid.UUID) -> list[dict]:
        query: Query = self._activity_and_flow_ids_by_subject_query(
            ActivityAssigmentSchema.target_subject_id, target_subject_id
        )

        res = await self._execute(query)

        return res.mappings().all()

    async def get_assignments_by_respondent_subject(self, respondent_subject_id: uuid.UUID) -> list[dict]:
        query: Query = self._activity_and_flow_ids_by_subject_query(
            ActivityAssigmentSchema.respondent_subject_id, respondent_subject_id
        )

        res = await self._execute(query)

        return res.mappings().all()
