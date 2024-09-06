import uuid
from typing import Literal

from sqlalchemy import or_, select, tuple_, update
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
        return await self._create_many(schemas)

    async def already_exists(self, schema: ActivityAssigmentSchema) -> bool:
        """
        Checks if an activity assignment already exists in the database.

        This method builds a query to check for the existence of an assignment with the same
        `activity_id`, `activity_flow_id`, `respondent_subject_id`, and `target_subject_id`,
        while ensuring the record has not been soft-deleted.

        Parameters:
        -----------
        schema : ActivityAssigmentSchema
            The activity assignment schema to check for existence.

        Returns:
        --------
        bool
            `True` if the assignment already exists, otherwise `False`.

        Notes:
        ------
        - This method uses the `_execute` method from the `BaseCRUD` class to run the query and
        check for the existence of the assignment.
        - The existence check is based on the combination of IDs and considers soft-deleted records.
        """
        query: Query = select(ActivityAssigmentSchema)
        query = query.where(ActivityAssigmentSchema.activity_id == schema.activity_id)
        query = query.where(ActivityAssigmentSchema.respondent_subject_id == schema.respondent_subject_id)
        query = query.where(ActivityAssigmentSchema.target_subject_id == schema.target_subject_id)
        query = query.where(ActivityAssigmentSchema.activity_flow_id == schema.activity_flow_id)
        query = query.where(ActivityAssigmentSchema.soft_exists())
        query = query.exists()
        db_result = await self._execute(select(query))
        return db_result.scalars().first() or False

    async def unassign_many(
        self,
        activity_or_flow_ids: list[uuid.UUID],
        respondent_subject_ids: list[uuid.UUID],
        target_subject_ids: list[uuid.UUID],
    ) -> None:
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

        query: Query = (
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
        await self._execute(query)

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

            query = query.where(or_(*activities_clause, *flows_clause))

        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_by_applet_and_subject(
        self,
        applet_id: uuid.UUID,
        subject_id: uuid.UUID,
        match_by: Literal["respondent", "target", "respondent_or_target"],
    ) -> list[ActivityAssigmentSchema]:
        respondent_schema = aliased(SubjectSchema)
        target_schema = aliased(SubjectSchema)

        if match_by == "respondent":
            match_clause = respondent_schema.id == subject_id
        elif match_by == "target":
            match_clause = target_schema.id == subject_id
        else:
            match_clause = or_(respondent_schema.id == subject_id, target_schema.id == subject_id)

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
                match_clause,
            )
        )

        db_result = await self._execute(query)

        return db_result.scalars().all()
