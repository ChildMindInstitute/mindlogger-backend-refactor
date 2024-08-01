import uuid
from collections import defaultdict

from apps.activities.crud import ActivitiesCRUD
from apps.activities.db.schemas import ActivitySchema
from apps.activity_assignments.crud.assignments import ActivityAssigmentCRUD
from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from apps.activity_assignments.domain.assignments import ActivityAssignment, ActivityAssignmentCreate
from apps.activity_flows.crud import FlowsCRUD
from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.invitations.crud import InvitationCRUD
from apps.invitations.domain import InvitationRespondent
from apps.shared.exception import ValidationError
from apps.subjects.crud import SubjectsCrud
from apps.subjects.domain import SubjectFull


class ActivityAssignmentService:
    class _AssigmentEntities:
        activities: dict[uuid.UUID, ActivitySchema]
        flows: dict[uuid.UUID, ActivityFlowSchema]
        invitations: dict[uuid.UUID, InvitationRespondent]
        respondents: dict[uuid.UUID, SubjectFull]
        target_subjects: dict[uuid.UUID, SubjectFull]

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
                invitation_id=assignment.invitation_id,
                respondent_id=assignment.respondent_id,
                target_subject_id=assignment.target_subject_id,
            )
            if await ActivityAssigmentCRUD(self.session).already_exists(schema):
                continue

            if activity_or_flow_name and assignment.respondent_id:
                respondent_activities[assignment.respondent_id].append(activity_or_flow_name)

            schemas.append(schema)

        assignment_schemas = await ActivityAssigmentCRUD(self.session).create_many(schemas)

        # Todo: send emails based on entities.respondent_activities array

        assignments = []
        for assignment in assignment_schemas:
            assignments.append(
                ActivityAssignment(
                    id=assignment.id,
                    activity_id=assignment.activity_id,
                    activity_flow_id=assignment.activity_flow_id,
                    invitation_id=assignment.invitation_id,
                    respondent_id=assignment.respondent_id,
                    target_subject_id=assignment.target_subject_id,
                )
            )
        return assignments

    async def _check_for_already_existing_assignment(self, schema: ActivityAssigmentSchema) -> bool:
        return await ActivityAssigmentCRUD(self.session).already_exists(schema)

    @staticmethod
    def _validate_assignment_and_get_activity_or_flow_name(
        assignment: ActivityAssignmentCreate, entities: _AssigmentEntities
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

        if assignment.invitation_id and entities.invitations.get(assignment.invitation_id) is None:
            raise ValidationError(f"Invalid invitation id {assignment.invitation_id} {activity_flow_message}")

        if assignment.respondent_id and entities.respondents.get(assignment.respondent_id) is None:
            raise ValidationError(f"Invalid respondent id {assignment.respondent_id} {activity_flow_message}")

        if assignment.target_subject_id and entities.target_subjects.get(assignment.target_subject_id) is None:
            raise ValidationError(f"Invalid target subject id {assignment.target_subject_id} {activity_flow_message}")

        return name

    async def _get_assignments_entities(self, applet_id, assignments_create) -> _AssigmentEntities:
        activity_ids = []
        flow_ids = []
        invitation_ids = []
        respondent_ids = []
        target_subject_ids = []
        for assignment in assignments_create:
            if assignment.activity_id:
                activity_ids.append(assignment.activity_id)
            if assignment.activity_flow_id:
                flow_ids.append(assignment.activity_flow_id)
            if assignment.invitation_id:
                invitation_ids.append(assignment.invitation_id)
            if assignment.respondent_id:
                respondent_ids.append(assignment.respondent_id)
            if assignment.target_subject_id:
                target_subject_ids.append(assignment.target_subject_id)

        entities = self._AssigmentEntities()
        entities.activities = {
            activity.id: activity
            for activity in await ActivitiesCRUD(self.session).get_by_applet_id_and_activities_ids(
                applet_id, activity_ids
            )
        }
        entities.flows = {
            flow.id: flow for flow in await FlowsCRUD(self.session).get_by_applet_id_and_flows_ids(applet_id, flow_ids)
        }
        entities.invitations = {
            invitation.id: invitation
            for invitation in await InvitationCRUD(self.session).get_pending_respondent_invitation_by_ids(
                applet_id, invitation_ids
            )
        }
        entities.respondents = {
            respondent.user_id: respondent
            for respondent in await SubjectsCrud(self.session).get_by_user_ids(applet_id, respondent_ids)
        }
        entities.target_subjects = {
            target_subject.id: target_subject
            for target_subject in await SubjectsCrud(self.session).get_by_ids(target_subject_ids)
            if target_subject.applet_id == applet_id
        }
        return entities
