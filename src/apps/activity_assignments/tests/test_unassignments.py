import http
import uuid

import pytest
from pydantic import EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from apps.activity_assignments.domain.assignments import ActivitiesAssignmentsCreate, ActivityAssignmentCreate
from apps.activity_flows.domain.flow_update import ActivityFlowItemUpdate, FlowUpdate
from apps.applets.domain.applet_create_update import AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.service import AppletService
from apps.invitations.domain import InvitationRespondentRequest
from apps.shared.enums import Language
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import Subject, SubjectCreate, SubjectFull
from apps.subjects.services import SubjectsService
from apps.users import User


# TODO: remove fixtures and import them from shared_fixtures.py
@pytest.fixture
def invitation_respondent_data() -> InvitationRespondentRequest:
    return InvitationRespondentRequest(
        email=EmailStr("pending@example.com"),
        first_name="User",
        last_name="pending",
        language="en",
        secret_user_id=str(uuid.uuid4()),
        nickname=str(uuid.uuid4()),
        tag="respondentTag",
    )


@pytest.fixture
async def lucy_applet_one_subject(session: AsyncSession, lucy: User, applet_one_lucy_respondent: AppletFull) -> Subject:
    applet_id = applet_one_lucy_respondent.id
    query = select(SubjectSchema).where(SubjectSchema.user_id == lucy.id, SubjectSchema.applet_id == applet_id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
async def lucy_applet_two_subject(session: AsyncSession, lucy: User, applet_two_lucy_respondent: AppletFull) -> Subject:
    applet_id = applet_two_lucy_respondent.id
    query = select(SubjectSchema).where(SubjectSchema.user_id == lucy.id, SubjectSchema.applet_id == applet_id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
async def applet_one_pending_subject(
    client,
    tom: User,
    invitation_respondent_data,
    applet_one: AppletFull,
    session: AsyncSession,
) -> Subject:
    # invite a new respondent
    client.login(tom)
    response = await client.post(
        "/invitations/{applet_id}/respondent".format(applet_id=str(applet_one.id)),
        invitation_respondent_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    query = select(SubjectSchema).where(
        SubjectSchema.applet_id == applet_one.id,
        SubjectSchema.email == invitation_respondent_data.email,
    )
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
async def applet_one_with_flow(
    session: AsyncSession,
    applet_one: AppletFull,
    applet_minimal_data: AppletFull,
    tom: User,
):
    data = AppletUpdate(**applet_minimal_data.dict())
    flow = FlowUpdate(
        name="flow",
        items=[ActivityFlowItemUpdate(id=None, activity_key=data.activities[0].key)],
        description={Language.ENGLISH: "description"},
        id=None,
    )
    data.activity_flows = [flow]
    srv = AppletService(session, tom.id)
    await srv.update(applet_one.id, data)
    applet = await srv.get_full_applet(applet_one.id)
    return applet


@pytest.fixture
async def applet_one_shell_account(session: AsyncSession, applet_one: AppletFull, tom: User) -> Subject:
    return await SubjectsService(session, tom.id).create(
        SubjectCreate(
            applet_id=applet_one.id,
            creator_id=tom.id,
            first_name="Shell",
            last_name="Account",
            nickname="shell-account-0",
            tag="shell-account-0-tag",
            secret_user_id=f"{uuid.uuid4()}",
        )
    )


class TestActivityUnassignments(BaseTest):
    activities_unassignments_applet = "/assignments/applet/{applet_id}/unassigns"
    activities_assignments_applet = "/assignments/applet/{applet_id}"

    async def test_create_one_unassignment(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        lucy_applet_one_subject: SubjectFull,
        tom_applet_one_subject,
        session: AsyncSession,
    ):
        client.login(tom)

        # Use the same details as the existing assignment
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=lucy_applet_one_subject.id,
                )
            ]
        )

        assignment_response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id),
            data=assignments_create,
        )

        assert assignment_response.status_code == http.HTTPStatus.CREATED, assignment_response.json()

        unassign_response = await client.delete(
            self.activities_unassignments_applet.format(applet_id=applet_one.id),
            data=assignments_create.dict(),
        )

        assert unassign_response.status_code == http.HTTPStatus.CREATED, unassign_response.json()
        assignments = unassign_response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one.activities[0].id)
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(lucy_applet_one_subject.id)
        assert assignment["activityFlowId"] is None
        assert assignment["id"] is not None

        query = select(ActivityAssigmentSchema).where(ActivityAssigmentSchema.id == assignment["id"])
        res = await session.execute(query, execution_options={"synchronize_session": False})
        model = res.scalars().one()

        assert str(model.id) == assignment["id"]
        assert model.activity_id == applet_one.activities[0].id
        assert model.is_deleted is True

    async def test_unassign_fail_wrong_activity(
        self,
        client: TestClient,
        applet_one: AppletFull,
        applet_two: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
    ):
        client.login(tom)

        # Step 1: Create an assignment in applet_two
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_two.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )
        await client.post(
            self.activities_assignments_applet.format(applet_id=applet_two.id),
            data=assignments_create,
        )

        # Step 2: Attempt to unassign it using the wrong applet_id (applet_one)
        unassignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_two.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        response = await client.delete(
            self.activities_unassignments_applet.format(applet_id=applet_one.id),
            data=unassignments_create.dict(),
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()
        result = response.json()["result"][0]
        assert result["message"] == f"Invalid activity id {applet_two.activities[0].id}"

    async def test_unassign_fail_missing_activity_and_flow(
        self,
        client: TestClient,
        applet_one: AppletFull,
        applet_two: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
    ):
        client.login(tom)

        # Step 1: Assign an activity first
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        # Create the assignment
        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id),
            data=assignments_create,
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Step 2: Attempt to unassign without providing activity_id or activity_flow_id
        unassignments_create = dict(
            assignments=[
                dict(
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        unassign_response = await client.delete(
            self.activities_unassignments_applet.format(applet_id=applet_one.id),
            data=unassignments_create,
        )

        assert unassign_response.status_code == http.HTTPStatus.BAD_REQUEST, unassign_response.json()
        result = unassign_response.json()["result"][0]
        assert result["message"] == "Either activity_id or activity_flow_id must be provided"

    async def test_unassign_fail_both_activity_and_flow(
        self,
        client: TestClient,
        applet_one: AppletFull,
        applet_two: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
    ):
        client.login(tom)

        # Step 1: Assign an activity first
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        # Create the assignment
        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id),
            data=assignments_create,
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Step 2: Attempt to unassign with both activity_id and activity_flow_id provided
        unassignments_create = dict(
            assignments=[
                dict(
                    activity_id=applet_one.activities[0].id,
                    activity_flow_id=applet_two.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        unassign_response = await client.delete(
            self.activities_unassignments_applet.format(applet_id=applet_one.id),
            data=unassignments_create,
        )

        assert unassign_response.status_code == http.HTTPStatus.BAD_REQUEST, unassign_response.json()
        result = unassign_response.json()["result"][0]
        assert result["message"] == "Only one of activity_id or activity_flow_id must be provided"

    async def test_unassign_multiple_assignments_with_flow(
        self,
        client: TestClient,
        applet_one_with_flow: AppletFull,
        tom: User,
        lucy_applet_one_subject: SubjectFull,
        tom_applet_one_subject: SubjectFull,
        session: AsyncSession,
    ):
        client.login(tom)

        # Step 1: Assign multiple activities/flows
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one_with_flow.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_flow_id=applet_one_with_flow.activity_flows[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=lucy_applet_one_subject.id,
                ),
            ]
        )

        # Create the assignments
        assignment_response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id),
            data=assignments_create,
        )

        assert assignment_response.status_code == http.HTTPStatus.CREATED, assignment_response.json()

        # Step 2: Unassign the previously assigned activities/flows
        unassignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one_with_flow.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_flow_id=applet_one_with_flow.activity_flows[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=lucy_applet_one_subject.id,
                ),
            ]
        )

        unassign_response = await client.delete(
            self.activities_unassignments_applet.format(applet_id=applet_one_with_flow.id),
            data=unassignments_create.dict(),
        )

        assert unassign_response.status_code == http.HTTPStatus.CREATED, unassign_response.json()
        unassignments = unassign_response.json()["result"]["assignments"]
        assert len(unassignments) == 2
        print(unassignments)
        # Validate that the assignments have been unassigned
        for unassignment in unassignments:
            query = select(ActivityAssigmentSchema).where(ActivityAssigmentSchema.id == unassignment["id"])
            res = await session.execute(query, execution_options={"synchronize_session": False})
            model = res.scalars().one()
            assert str(model.id) == unassignment["id"]
            assert model.is_deleted is True

    async def test_unassign_fail_wrong_flow(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        applet_one_with_flow: AppletFull,
    ):
        client.login(tom)

        # Step 1: Assign an activity with a valid flow
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_flow_id=applet_one_with_flow.activity_flows[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        # Create the assignment
        assign_response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id),
            data=assignments_create.dict(),
        )
        assert assign_response.status_code == http.HTTPStatus.CREATED, assign_response.json()

        # Step 2: Attempt to unassign with a wrong flow_id
        fake_flow_id = uuid.uuid4()  # Generate a fake flow_id that does not exist
        unassignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_flow_id=fake_flow_id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        # Attempt to unassign
        unassign_response = await client.delete(
            self.activities_unassignments_applet.format(applet_id=applet_one.id),
            data=unassignments_create.dict(),
        )

        # Assert that the response indicates failure due to the wrong flow ID
        assert unassign_response.status_code == http.HTTPStatus.BAD_REQUEST, unassign_response.json()
        result = unassign_response.json()["result"][0]
        assert result["message"] == f"Invalid flow id {fake_flow_id}"

    async def test_unassign_with_pending_subject(
        self,
        client: TestClient,
        applet_one_with_flow: AppletFull,
        tom: User,
        applet_one_pending_subject: Subject,
        session: AsyncSession,
    ):
        client.login(tom)

        # Step 1: Assign an activity and a flow to the pending subject
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one_with_flow.activities[0].id,
                    respondent_subject_id=applet_one_pending_subject.id,
                    target_subject_id=applet_one_pending_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_flow_id=applet_one_with_flow.activity_flows[0].id,
                    respondent_subject_id=applet_one_pending_subject.id,
                    target_subject_id=applet_one_pending_subject.id,
                ),
            ]
        )

        # Create the assignment
        assign_response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id),
            data=assignments_create.dict(),
        )
        assert assign_response.status_code == http.HTTPStatus.CREATED, assign_response.json()

        # Step 2: Unassign the created activities and flow
        unassignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one_with_flow.activities[0].id,
                    respondent_subject_id=applet_one_pending_subject.id,
                    target_subject_id=applet_one_pending_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_flow_id=applet_one_with_flow.activity_flows[0].id,
                    respondent_subject_id=applet_one_pending_subject.id,
                    target_subject_id=applet_one_pending_subject.id,
                ),
            ]
        )

        # Unassign the assignment
        unassign_response = await client.delete(
            self.activities_unassignments_applet.format(applet_id=applet_one_with_flow.id),
            data=unassignments_create.dict(),
        )

        assert unassign_response.status_code == http.HTTPStatus.CREATED, assign_response.json()
        unassignments = unassign_response.json()["result"]["assignments"]
        assert len(unassignments) == 2
        assert unassignments[0]["activityId"] == str(applet_one_with_flow.activities[0].id)
        assert unassignments[0]["respondentSubjectId"] == str(applet_one_pending_subject.id)
        assert unassignments[0]["targetSubjectId"] == str(applet_one_pending_subject.id)

        assert unassignments[1]["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)
        assert unassignments[1]["respondentSubjectId"] == str(applet_one_pending_subject.id)
        assert unassignments[1]["targetSubjectId"] == str(applet_one_pending_subject.id)

        for unassignment in unassignments:
            query = select(ActivityAssigmentSchema).where(ActivityAssigmentSchema.id == unassignment["id"])
            res = await session.execute(query, execution_options={"synchronize_session": False})
            model = res.scalars().one()
            assert str(model.id) == unassignment["id"]
            assert model.is_deleted is True

    async def test_unassign_fail_wrong_respondent(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        lucy_applet_two_subject: SubjectFull,
        tom_applet_one_subject: SubjectFull,
        session: AsyncSession,
    ):
        client.login(tom)

        # Step 1: Assign an activity to a valid respondent and target
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        # Create the assignment
        assign_response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id),
            data=assignments_create.dict(),
        )
        assert assign_response.status_code == http.HTTPStatus.CREATED, assign_response.json()

        # Step 2: Attempt to unassign using a wrong respondent subject ID (lucy_applet_two_subject)
        unassignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=lucy_applet_two_subject.id,
                    target_subject_id=lucy_applet_two_subject.id,
                )
            ]
        )

        unassign_response = await client.delete(
            self.activities_unassignments_applet.format(applet_id=applet_one.id),
            data=unassignments_create.dict(),
        )

        # Assert that the response indicates failure due to the wrong respondent subject ID
        assert unassign_response.status_code == http.HTTPStatus.BAD_REQUEST, unassign_response.json()
        result = unassign_response.json()["result"][0]
        assert (
            result["message"]
            == f"Invalid respondent subject id {lucy_applet_two_subject.id} for assignment to activity test"
        )

        # Query the database to ensure the original assignment is still present
        query = select(ActivityAssigmentSchema).where(
            ActivityAssigmentSchema.activity_id == applet_one.activities[0].id,
            ActivityAssigmentSchema.respondent_subject_id == tom_applet_one_subject.id,
            ActivityAssigmentSchema.target_subject_id == tom_applet_one_subject.id,
            ActivityAssigmentSchema.is_deleted.is_(False),
        )

        res = await session.execute(query, execution_options={"synchronize_session": False})
        assignment = res.scalars().one_or_none()

        assert assignment is not None  # Ensure the original assignment was not removed

    async def test_unassign_fail_shell_account_respondent(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        applet_one_shell_account: SubjectFull,
        session: AsyncSession,
    ):
        client.login(tom)

        # Step 1: Assign an activity with a valid respondent and target subject
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        # Create the assignment
        assign_response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id),
            data=assignments_create.dict(),
        )
        assert assign_response.status_code == http.HTTPStatus.CREATED, assign_response.json()

        # Step 2: Attempt to unassign using a shell account as the respondent
        unassignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=applet_one_shell_account.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        unassign_response = await client.delete(
            self.activities_unassignments_applet.format(applet_id=applet_one.id),
            data=unassignments_create.dict(),
        )

        # Assert that the response indicates failure due to the shell account as the respondent subject
        assert unassign_response.status_code == http.HTTPStatus.BAD_REQUEST, unassign_response.json()
        result = unassign_response.json()["result"][0]
        assert (
            result["message"]
            == f"Invalid respondent subject id {applet_one_shell_account.id} for assignment to activity test"
        )

        # Query the database to ensure the original assignment is still present
        query = select(ActivityAssigmentSchema).where(
            ActivityAssigmentSchema.activity_id == applet_one.activities[0].id,
            ActivityAssigmentSchema.respondent_subject_id == tom_applet_one_subject.id,
            ActivityAssigmentSchema.target_subject_id == tom_applet_one_subject.id,
            ActivityAssigmentSchema.is_deleted.is_(False),
        )
        res = await session.execute(query, execution_options={"synchronize_session": False})
        assignment = res.scalars().one_or_none()

        assert assignment is not None  # Ensure the original assignment was not removed

    async def test_unassign_shell_account_target(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        applet_one_shell_account,
        session: AsyncSession,
    ):
        client.login(tom)

        # Step 1: Assign an activity with a shell account as the target
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=applet_one_shell_account.id,
                )
            ]
        )

        # Create the assignment
        assign_response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id),
            data=assignments_create.dict(),
        )
        assert assign_response.status_code == http.HTTPStatus.CREATED, assign_response.json()

        # Verify the assignment was created successfully
        assignments = assign_response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one.activities[0].id)
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(applet_one_shell_account.id)
        assert assignment["activityFlowId"] is None
        assert assignment["id"] is not None

        # Step 2: Unassign the activity with the shell account as the target
        unassignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=applet_one_shell_account.id,
                )
            ]
        )

        unassign_response = await client.delete(
            self.activities_unassignments_applet.format(applet_id=applet_one.id),
            data=unassignments_create.dict(),
        )

        # Verify that the unassignment was successful
        assert unassign_response.status_code == http.HTTPStatus.CREATED, unassign_response.json()
        assignments = unassign_response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one.activities[0].id)
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(applet_one_shell_account.id)
        assert assignment["activityFlowId"] is None

        # Query the database to validate the unassignment
        query = select(ActivityAssigmentSchema).where(ActivityAssigmentSchema.id == assignment["id"])
        res = await session.execute(query)
        model = res.scalars().one()

        assert model.is_deleted is True
        assert str(model.id) == assignment["id"]
        assert model.activity_id == uuid.UUID(assignment["activityId"])
        assert model.respondent_subject_id == uuid.UUID(assignment["respondentSubjectId"])
        assert model.target_subject_id == uuid.UUID(assignment["targetSubjectId"])

    async def test_unassign_fail_wrong_target(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
    ):
        client.login(tom)

        # Step 1: Assign a valid activity with correct target subject
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        # Create the assignment
        assign_response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id),
            data=assignments_create.dict(),
        )
        assert assign_response.status_code == http.HTTPStatus.CREATED, assign_response.json()

        # Step 2: Attempt to unassign with an invalid target subject
        unassignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=uuid.UUID("7db2b7fe-3eba-4c70-8d02-dcf55b74d1c3"),  # Invalid target subject ID
                )
            ]
        )

        unassign_response = await client.delete(
            self.activities_unassignments_applet.format(applet_id=applet_one.id),
            data=unassignments_create.dict(),
        )

        # Validate the response indicates failure due to the wrong target subject ID
        assert unassign_response.status_code == http.HTTPStatus.BAD_REQUEST, unassign_response.json()
        result = unassign_response.json()["result"][0]
        assert (
            result["message"]
            == "Invalid target subject id 7db2b7fe-3eba-4c70-8d02-dcf55b74d1c3 for assignment to activity test"
        )
