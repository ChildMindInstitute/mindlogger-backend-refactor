from sqlalchemy import select, or_
from sqlalchemy.orm import Query
import uuid

from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from infrastructure.database import BaseCRUD

__all__ = ["ActivityAssigmentCRUD"]


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
    
    
    async def unassign_many(self, schemas: list[ActivityAssigmentSchema]) -> list[ActivityAssigmentSchema]:
        """
        Unassigns multiple assignments by marking them as deleted.

        This method updates the `is_deleted` field for multiple assignment records
        based on their `id`.

        Parameters:
        ----------
        schemas : list[ActivityAssigmentSchema]
            A list of schemas that need to be updated (unassigned).

        Returns:
        -------
        list[ActivityAssigmentSchema]
            A list of updated assignment schemas.
        """
        updated_schemas = []
        for schema in schemas:
            updated_schemas.extend(
                await self._update(
                    lookup='id',
                    value=schema.id,
                    schema=schema
                )
            )
        return updated_schemas
    
    
    async def get_assignments_by_activity_or_flow_id_and_subject_id(
        self,
        search_id: uuid.UUID,
        respondent_subject_id: uuid.UUID,
        target_subject_id: uuid.UUID,
    ) -> uuid.UUID | None:
        """
        Retrieves the assignment ID from the activity_assignment table that matches
        the given activity ID or flow ID and the respondent subject ID or target subject ID.

        Parameters:
        ----------
        search_id : uuid.UUID
            The ID to search for, either an activity ID or a flow ID.
        respondent_subject_id : uuid.UUID
            The ID of the respondent subject to match.
        
        target_subject_id : uuid.UUID
            The ID of the target subject to match.

        Returns:
        -------
        uuid.UUID | None
            The ID of the matching assignment, or None if no match is found.
        """

        # Construct the query to match either activity_id or activity_flow_id and either subject ID
        query: Query = select(ActivityAssigmentSchema)
        query= query.where(
            or_(
                ActivityAssigmentSchema.activity_id == search_id,
                ActivityAssigmentSchema.activity_flow_id == search_id
            )
        )
        query = query.where(
            or_(
                ActivityAssigmentSchema.respondent_subject_id == respondent_subject_id,
                ActivityAssigmentSchema.target_subject_id == target_subject_id
            )
        )
        # Execute the query
        result = await self._execute(query)

        # Fetch the first matching assignment and return its ID, or None if no match is found
        assignment = result.scalars().first()
        return assignment.id if assignment else None