import uuid
from collections import defaultdict

from apps.activities.crud import ActivitiesCRUD
from apps.activities.db.schemas import ActivitySchema
from apps.activity_assignments.crud.assignments import ActivityAssigmentCRUD
from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from apps.activity_assignments.domain.assignments import ActivityAssignment, ActivityAssignmentCreate
from apps.activity_flows.crud import FlowsCRUD
from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.shared.exception import ValidationError
from apps.subjects.crud import SubjectsCrud
from apps.subjects.db.schemas import SubjectSchema


class ActivityAssignmentService:
    class _AssignmentEntities:
        activities: dict[uuid.UUID, ActivitySchema]
        flows: dict[uuid.UUID, ActivityFlowSchema]
        respondent_subjects: dict[uuid.UUID, SubjectSchema]
        target_subjects: dict[uuid.UUID, SubjectSchema]

    def __init__(self, session):
        self.session = session

    async def create_many(
        self, applet_id: uuid.UUID, assignments_create: list[ActivityAssignmentCreate]
    ) -> list[ActivityAssignment]:
        """
        Creates multiple activity assignments for the given applet.

        This method takes a list of assignment creation requests, validates them, checks for
        existing assignments, and then creates new assignments in the database. If an assignment 
        already exists, it is skipped. The method returns the successfully created assignments.

        Parameters:
        -----------
        applet_id : uuid.UUID
            The ID of the applet for which the assignments are being created.

        assignments_create : list[ActivityAssignmentCreate]
            A list of assignment creation objects that specify the details of each assignment.
            Each object contains information such as `activity_id`, `activity_flow_id`, 
            `respondent_subject_id`, and `target_subject_id`.

        Returns:
        --------
        list[ActivityAssignment]
            A list of `ActivityAssignment` objects that have been successfully created.

        Process:
        --------
        1. Retrieves all relevant entities (activities, flows, subjects) using 
        `_get_assignments_entities`.
        2. Validates each assignment and retrieves the corresponding activity or flow name 
        using `_validate_assignment_and_get_activity_or_flow_name`.
        3. Checks if the assignment already exists using `ActivityAssigmentCRUD.already_exists`.
        If it does, the assignment is skipped.
        4. Creates a new `ActivityAssigmentSchema` for each valid assignment and collects them 
        into a list.
        5. Inserts the new assignments into the database using `ActivityAssigmentCRUD.create_many`.
        6. Optionally, stores respondent activities for future processing (e.g., sending emails).
        (This step is marked as a TODO.)
        7. Returns the newly created `ActivityAssignment` objects.

        """
        entities = await self._get_assignments_entities(applet_id, assignments_create)

        respondent_activities: dict[uuid.UUID, list[str]] = defaultdict(list)
        schemas = []
        for assignment in assignments_create:
            activity_or_flow_name: str = self._validate_assignment_and_get_activity_or_flow_name(assignment, entities)
            schema = ActivityAssigmentSchema(
                id=uuid.uuid4(),
                activity_id=assignment.activity_id,
                activity_flow_id=assignment.activity_flow_id,
                respondent_subject_id=assignment.respondent_subject_id,
                target_subject_id=assignment.target_subject_id,
            )
            if await ActivityAssigmentCRUD(self.session).already_exists(schema):
                continue

            if entities.respondent_subjects[assignment.respondent_subject_id].user_id:
                respondent_activities[assignment.respondent_subject_id].append(activity_or_flow_name)

            schemas.append(schema)

        assignment_schemas: list[ActivityAssigmentSchema] = await ActivityAssigmentCRUD(self.session).create_many(
            schemas
        )

        # Todo: send emails based on respondent_activities array

        return [
            ActivityAssignment(
                id=assignment.id,
                activity_id=assignment.activity_id,
                activity_flow_id=assignment.activity_flow_id,
                respondent_subject_id=assignment.respondent_subject_id,
                target_subject_id=assignment.target_subject_id,
            )
            for assignment in assignment_schemas
        ]

    async def _check_for_already_existing_assignment(self, schema: ActivityAssigmentSchema) -> bool:
        return await ActivityAssigmentCRUD(self.session).already_exists(schema)

    @staticmethod
    def _validate_assignment_and_get_activity_or_flow_name(
        assignment: ActivityAssignmentCreate, entities: _AssignmentEntities
    ) -> str:
        """
        Validates the assignment request and retrieves the name of the activity or flow.

        This method checks the validity of the provided `activity_id`, `activity_flow_id`, 
        `respondent_subject_id`, and `target_subject_id` by ensuring they correspond to existing 
        records. If validation passes, it returns the name of the activity or flow. If any validation 
        fails, it raises a `ValidationError`.

        Parameters:
        ----------
        assignment : ActivityAssignmentCreate
            The assignment request object containing the details of the assignment, 
            including `activity_id`, `activity_flow_id`, `respondent_subject_id`, and `target_subject_id`.
        
        entities : _AssignmentEntities
            A collection of entities that includes activities, flows, respondent subjects, 
            and target subjects, used for validation.

        Returns:
        -------
        str
            The name of the activity or flow corresponding to the assignment.

        Raises:
        ------
        ValidationError
            If any of the following conditions are met:
            - The `activity_id` provided does not correspond to an existing activity.
            - The `activity_flow_id` provided does not correspond to an existing activity flow.
            - The `respondent_subject_id` provided does not correspond to an existing respondent subject.
            - The `target_subject_id` provided does not correspond to an existing target subject.
        """
        name: str = ""
        activity_flow_message = ""
        if assignment.activity_id:
            if (activity := entities.activities.get(assignment.activity_id)) is None:
                raise ValidationError(f"Invalid activity id {assignment.activity_id}")

            activity_flow_message = f"for assignment to activity {activity.name}"
            name = activity.name

        if assignment.activity_flow_id:
            if (flow := entities.flows.get(assignment.activity_flow_id)) is None:
                raise ValidationError(f"Invalid flow id {assignment.activity_flow_id}")

            activity_flow_message = f"for assignment to activity flow {flow.name}"
            name = flow.name

        if entities.respondent_subjects.get(assignment.respondent_subject_id) is None:
            raise ValidationError(
                f"Invalid respondent subject id {assignment.respondent_subject_id} {activity_flow_message}"
            )

        if entities.target_subjects.get(assignment.target_subject_id) is None:
            raise ValidationError(f"Invalid target subject id {assignment.target_subject_id} {activity_flow_message}")

        return name

    async def _get_assignments_entities(
        self, applet_id: uuid.UUID, assignments_create: list[ActivityAssignmentCreate]
    ) -> _AssignmentEntities:
        activity_ids = []
        flow_ids = []
        target_subject_ids = []
        respondent_subject_ids = []
        for assignment in assignments_create:
            if assignment.activity_id:
                activity_ids.append(assignment.activity_id)
            if assignment.activity_flow_id:
                flow_ids.append(assignment.activity_flow_id)
            respondent_subject_ids.append(assignment.respondent_subject_id)
            target_subject_ids.append(assignment.target_subject_id)

        entities = self._AssignmentEntities()
        entities.activities = {
            activity.id: activity
            for activity in await ActivitiesCRUD(self.session).get_by_applet_id_and_activities_ids(
                applet_id, activity_ids
            )
        }
        entities.flows = {
            flow.id: flow for flow in await FlowsCRUD(self.session).get_by_applet_id_and_flows_ids(applet_id, flow_ids)
        }

        entities.respondent_subjects = {
            subject.id: subject
            for subject in await SubjectsCrud(self.session).get_by_ids(respondent_subject_ids)
            if subject.applet_id == applet_id and subject.email is not None
        }

        entities.target_subjects = {
            subject.id: subject
            for subject in await SubjectsCrud(self.session).get_by_ids(target_subject_ids)
            if subject.applet_id == applet_id
        }

        return entities
    
    async def _get_assignment_by_activity_or_flow_and_subject_id(
        self, assignment: ActivityAssignmentCreate
    ) -> uuid.UUID:
        activity_id = assignment.activity_id
        flow_id = assignment.activity_flow_id
        respondent_subject_id = assignment.respondent_subject_id
        target_subject_id = assignment.target_subject_id

        entities = self._AssignmentEntities()
        search_id = flow_id if flow_id is not None else activity_id
        assignment_id = await ActivityAssigmentCRUD(self.session).get_assignments_by_activity_or_flow_id_and_subject_id(
                    search_id=search_id,
                    respondent_subject_id=respondent_subject_id,
                    target_subject_id=target_subject_id
                )
        return assignment_id
    
    
    async def unassign_many(
        self, applet_id: uuid.UUID, assignments_unassign: list[ActivityAssignmentCreate]
    ) -> list[ActivityAssignment]:
        """
        Unassigns multiple activity assignments by marking them as deleted.

        This method takes a list of assignment requests, retrieves the corresponding 
        assignment entities from the database, marks them as deleted, and then returns 
        the updated assignments.

        Parameters:
        -----------
        applet_id : uuid.UUID
            The ID of the applet for which the assignments are being unassigned.

        assignments_unassign : list[ActivityAssignmentCreate]
            A list of assignment creation objects that specify which assignments to unassign.
            Each object contains details such as `activity_id`, `activity_flow_id`, 
            `respondent_subject_id`, and `target_subject_id`.

        Returns:
        --------
        list[ActivityAssignment]
            A list of `ActivityAssignment` objects that have been marked as deleted.

        Process:
        --------
        1. Retrieves all relevant entities (activities, flows, subjects) using 
        `_get_assignments_entities`.
        2. Validates each assignment and retrieves the corresponding assignment ID 
        using `_get_assignment_by_activity_or_flow_and_subject_id`.
        3. Creates a schema for each assignment, marking it as deleted.
        4. Unassigns the assignments in the database using `ActivityAssigmentCRUD.unassign_many`.
        5. Optionally, sends emails based on the respondent activities (not yet implemented).
        6. Returns a list of the updated `ActivityAssignment` objects.

        """
        entities = await self._get_assignments_entities(applet_id, assignments_unassign)

        respondent_activities: dict[uuid.UUID, list[str]] = defaultdict(list)
        schemas = []
        for assignment in assignments_unassign:
            activity_or_flow_name: str = self._validate_assignment_and_get_activity_or_flow_name(assignment, entities)
            
            id_assignment = await self._get_assignment_by_activity_or_flow_and_subject_id(assignment)
            schema = ActivityAssigmentSchema(
                id=id_assignment,
                activity_id=assignment.activity_id,
                activity_flow_id=assignment.activity_flow_id,
                respondent_subject_id=assignment.respondent_subject_id,
                target_subject_id=assignment.target_subject_id,
                is_deleted=True,
            )
            
            if entities.respondent_subjects[assignment.respondent_subject_id].user_id:
                respondent_activities[assignment.respondent_subject_id].append(activity_or_flow_name)

            schemas.append(schema)

        assignment_schemas: list[ActivityAssigmentSchema] = await ActivityAssigmentCRUD(self.session).unassign_many(
            schemas
        )
        
        # Todo: send emails based on respondent_activities array

        return [
            ActivityAssignment(
                id=assignment.id,
                activity_id=assignment.activity_id,
                activity_flow_id=assignment.activity_flow_id,
                respondent_subject_id=assignment.respondent_subject_id,
                target_subject_id=assignment.target_subject_id,
                is_deleted=assignment.is_deleted,

            )
            for assignment in assignment_schemas
        ]
