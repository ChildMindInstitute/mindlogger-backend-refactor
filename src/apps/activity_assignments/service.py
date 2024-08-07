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
