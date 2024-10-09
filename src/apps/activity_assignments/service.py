import asyncio
import uuid
from collections import defaultdict

from apps.activities.crud import ActivitiesCRUD
from apps.activities.db.schemas import ActivitySchema
from apps.activity_assignments.crud.assignments import ActivityAssigmentCRUD
from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from apps.activity_assignments.domain.assignments import (
    ActivityAssignment,
    ActivityAssignmentCreate,
    ActivityAssignmentDelete,
    ActivityAssignmentWithSubject,
)
from apps.activity_flows.crud import FlowsCRUD
from apps.activity_flows.db.schemas import ActivityFlowSchema
from apps.applets.crud import AppletsCRUD
from apps.invitations.crud import InvitationCRUD
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.shared.exception import NotFoundError, ValidationError
from apps.shared.query_params import QueryParams
from apps.subjects.crud import SubjectsCrud
from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import SubjectReadResponse
from config import settings


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

        respondent_activities: dict[uuid.UUID, set[str]] = defaultdict(set)
        assignment_schemas = []
        for assignment in assignments_create:
            activity_or_flow_name: str = self._validate_assignment_and_get_activity_or_flow_name(assignment, entities)
            data = dict(
                activity_flow_id=assignment.activity_flow_id,
                activity_id=assignment.activity_id,
                respondent_subject_id=assignment.respondent_subject_id,
                target_subject_id=assignment.target_subject_id,
            )

            schema: ActivityAssigmentSchema | None = await ActivityAssigmentCRUD(self.session).upsert(data)
            if schema is None:
                continue

            assignment_schemas.append(schema)

            pending_invitation = await InvitationCRUD(self.session).get_pending_subject_invitation(
                applet_id, assignment.respondent_subject_id
            )
            if not pending_invitation:
                respondent_activities[assignment.respondent_subject_id].add(activity_or_flow_name)

        await self.send_email_notification(applet_id, entities.respondent_subjects, respondent_activities)

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

    async def check_for_assignment_and_notify(self, applet_id: uuid.UUID, respondent_subject_id: uuid.UUID) -> None:
        query_params = QueryParams(filters={"respondent_subject_id": respondent_subject_id})
        assignments = await ActivityAssigmentCRUD(self.session).get_by_applet(applet_id, query_params)
        if not assignments:
            return

        activity_ids = []
        flow_ids = []
        for assignment in assignments:
            if assignment.activity_id:
                activity_ids.append(assignment.activity_id)
            if assignment.activity_flow_id:
                flow_ids.append(assignment.activity_flow_id)

        activities = {
            activity.id: activity
            for activity in await ActivitiesCRUD(self.session).get_by_applet_id_and_activities_ids(
                applet_id, activity_ids
            )
        }
        flows = {
            flow.id: flow for flow in await FlowsCRUD(self.session).get_by_applet_id_and_flows_ids(applet_id, flow_ids)
        }

        respondent_subject = await SubjectsCrud(self.session).get_by_id(respondent_subject_id)
        assert respondent_subject

        respondent_activities: dict[uuid.UUID, set[str]] = defaultdict(set)
        for assignment in assignments:
            activity_or_flow = activities.get(assignment.activity_id) or flows.get(assignment.activity_flow_id)
            if activity_or_flow:
                respondent_activities[respondent_subject_id].add(activity_or_flow.name)

        if len(respondent_activities[respondent_subject_id]) > 0:
            await self.send_email_notification(
                applet_id,
                {respondent_subject_id: respondent_subject},
                respondent_activities,
            )

    async def send_email_notification(
        self,
        applet_id: uuid.UUID,
        subjects: dict[uuid.UUID, SubjectSchema],
        respondent_activities: dict[uuid.UUID, set[str]],
    ) -> None:
        service = MailingService()
        applet = await AppletsCRUD(self.session).get_by_id(applet_id)
        for respondent_subject_id, activities in respondent_activities.items():
            respondent_subject: SubjectSchema = subjects[respondent_subject_id]

            language = respondent_subject.language or "en"

            domain = settings.service.urls.frontend.web_base
            path = settings.service.urls.frontend.applet_home
            link = (
                f"https://{domain}/{path}/{applet.id}"
                if not domain.startswith("http")
                else f"{domain}/{path}/{applet.id}"
            )

            message = MessageSchema(
                recipients=[respondent_subject.email],
                subject=self._get_email_assignment_subject(language),
                body=service.get_localized_html_template(
                    _template_name=self._get_email_template_name(),
                    _language=language,
                    first_name=respondent_subject.first_name,
                    applet_name=applet.display_name,
                    link=link,
                    activity_or_flows_names=activities,
                ),
            )
            _ = asyncio.create_task(service.send(message))

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

    async def unassign_many(self, assignments_unassign: list[ActivityAssignmentDelete]) -> None:
        """
        Unassigns multiple activity assignments by marking them as deleted.

        This method takes a list of assignment requests, retrieves the corresponding
        assignment entities from the database, marks them as deleted, and then returns
        the updated assignments.

        Parameters:
        -----------
        assignments_unassign : list[ActivityAssignmentDelete]
            A list of assignment creation objects that specify which assignments to unassign.
            Each object contains details such as `activity_id`, `activity_flow_id`,
            `respondent_subject_id`, and `target_subject_id`.

        Returns:
        --------
        list[ActivityAssignment]
            A list of `ActivityAssignment` objects that have been marked as deleted.
        """

        activity_or_flow_ids = []
        respondent_subject_ids = []
        target_subject_ids = []

        for assignment in assignments_unassign:
            activity_or_flow_ids.append(assignment.activity_id or assignment.activity_flow_id)
            target_subject_ids.append(assignment.target_subject_id)
            respondent_subject_ids.append(assignment.respondent_subject_id)

        await ActivityAssigmentCRUD(self.session).delete_many(
            activity_or_flow_ids=activity_or_flow_ids,  # type: ignore
            respondent_subject_ids=respondent_subject_ids,
            target_subject_ids=target_subject_ids,
        )

    async def delete_by_activity_or_flow_ids(self, activity_or_flow_ids: list[uuid.UUID]) -> None:
        await ActivityAssigmentCRUD(self.session).delete_by_activity_or_flow_ids(activity_or_flow_ids)

    async def get_all(self, applet_id: uuid.UUID, query_params: QueryParams) -> list[ActivityAssignment]:
        """
        Returns assignments for given applet ID and matching any filters provided in query_params.
        """
        assignments = await ActivityAssigmentCRUD(self.session).get_by_applet(applet_id, query_params)

        return [
            ActivityAssignment(
                id=assignment.id,
                activity_id=assignment.activity_id,
                activity_flow_id=assignment.activity_flow_id,
                respondent_subject_id=assignment.respondent_subject_id,
                target_subject_id=assignment.target_subject_id,
            )
            for assignment in assignments
        ]

    async def get_all_with_subject_entities(
        self,
        applet_id: uuid.UUID,
        query_params: QueryParams,
    ) -> list[ActivityAssignmentWithSubject]:
        """
        Returns assignments for given applet ID and matching any filters provided in query_params, with
        respondent_subject and target_subject properties containing hydrated subject entities.
        """
        for subject_id in set(query_params.filters.values()):
            subject_exists = await SubjectsCrud(self.session).exist(subject_id, applet_id)
            if not subject_exists:
                raise NotFoundError(f"Subject with id {subject_id} not found")

        assignments = await ActivityAssigmentCRUD(self.session).get_by_applet(applet_id, query_params)

        subject_ids: set[uuid.UUID] = set()
        for assignment in assignments:
            subject_ids.add(assignment.respondent_subject_id)
            subject_ids.add(assignment.target_subject_id)

        subjects = {
            subject.id: SubjectReadResponse(
                id=subject.id,
                first_name=subject.first_name,
                last_name=subject.last_name,
                email=subject.email,
                language=subject.language,
                nickname=subject.nickname,
                secret_user_id=subject.secret_user_id,
                tag=subject.tag,
                applet_id=subject.applet_id,
            )
            for subject in await SubjectsCrud(self.session).get_by_ids(list(subject_ids))
        }

        return [
            ActivityAssignmentWithSubject(
                id=assignment.id,
                activity_id=assignment.activity_id,
                activity_flow_id=assignment.activity_flow_id,
                respondent_subject=subjects[assignment.respondent_subject_id],
                target_subject=subjects[assignment.target_subject_id],
            )
            for assignment in assignments
        ]

    async def get_target_subject_ids_by_respondent(
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
        return await ActivityAssigmentCRUD(self.session).get_target_subject_ids_by_activity_or_flow_ids(
            respondent_subject_id, activity_or_flow_ids
        )

    async def check_if_auto_assigned(self, activity_or_flow_id: uuid.UUID) -> bool | None:
        """
        Checks if the activity or flow is currently set to auto-assign.
        """
        return await ActivityAssigmentCRUD(self.session).check_if_auto_assigned(activity_or_flow_id)

    @staticmethod
    def _get_email_template_name() -> str:
        return "new_activity_assignments"

    @staticmethod
    def _get_email_assignment_subject(language: str) -> str:
        translations = {
            "en": "Assignment Notification",
            "fr": "Notification d'attribution",
        }
        return translations.get(language, translations["en"])
