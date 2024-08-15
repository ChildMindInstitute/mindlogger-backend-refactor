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
    client, tom: User, invitation_respondent_data, applet_one: AppletFull, session: AsyncSession
) -> Subject:
    # invite a new respondent
    client.login(tom)
    response = await client.post(
        "/invitations/{applet_id}/respondent".format(applet_id=str(applet_one.id)),
        invitation_respondent_data,
    )
    assert response.status_code == http.HTTPStatus.OK

    query = select(SubjectSchema).where(
        SubjectSchema.applet_id == applet_one.id, SubjectSchema.email == invitation_respondent_data.email
    )
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
async def applet_one_with_flow(
    session: AsyncSession, applet_one: AppletFull, applet_minimal_data: AppletFull, tom: User
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


class TestActivityAssignments(BaseTest):
    activities_assignments_applet = "/assignments/applet/{applet_id}"

    async def test_create_one_assignment(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        lucy_applet_one_subject: SubjectFull,
        tom_applet_one_subject,
        session: AsyncSession,
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=lucy_applet_one_subject.id,
                )
            ]
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        assignments = response.json()["result"]["assignments"]
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

    async def test_create_assignment_fail_wrong_activity(
        self,
        client: TestClient,
        applet_one: AppletFull,
        applet_two: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_two.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]  # activity from applet two
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()
        result = response.json()["result"][0]
        assert result["message"] == f"Invalid activity id {applet_two.activities[0].id}"

    async def test_create_assignment_fail_missing_activity_and_flow(
        self,
        client: TestClient,
        applet_one: AppletFull,
        applet_two: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
    ):
        client.login(tom)

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id),
            data=dict(
                assignments=[
                    dict(
                        respondent_subject_id=tom_applet_one_subject.id,
                        target_subject_id=tom_applet_one_subject.id,
                    )
                ]
            ),
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()
        result = response.json()["result"][0]
        assert result["message"] == "Either activity_id or activity_flow_id must be provided"

    async def test_create_assignment_fail_both_activity_and_flow(
        self,
        client: TestClient,
        applet_one: AppletFull,
        applet_two: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
    ):
        client.login(tom)

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id),
            data=dict(
                assignments=[
                    dict(
                        activity_id=applet_two.activities[0].id,
                        activity_flow_id=applet_two.activities[0].id,
                        respondent_subject_id=tom_applet_one_subject.id,
                        target_subject_id=tom_applet_one_subject.id,
                    )
                ]
            ),
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()
        result = response.json()["result"][0]
        assert result["message"] == "Only one of activity_id or activity_flow_id must be provided"

    async def test_create_multiple_assignments_with_flow(
        self,
        client: TestClient,
        applet_one_with_flow: AppletFull,
        tom: User,
        lucy_applet_one_subject: SubjectFull,
        tom_applet_one_subject: SubjectFull,
    ):
        client.login(tom)

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

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 2

        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one_with_flow.activities[0].id)
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["activityFlowId"] is None

        assignment = assignments[1]
        assert assignment["activityId"] is None
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(lucy_applet_one_subject.id)
        assert assignment["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)

    async def test_create_assignment_fail_wrong_flow(
        self, client: TestClient, applet_one: AppletFull, tom: User, tom_applet_one_subject: SubjectFull
    ):
        client.login(tom)

        fake_flow_id = uuid.uuid4()
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_flow_id=fake_flow_id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]  # flow do not exists
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()
        result = response.json()["result"][0]
        assert result["message"] == f"Invalid flow id {fake_flow_id}"

    async def test_create_assignments_with_pending_subject(
        self, client: TestClient, applet_one_with_flow: AppletFull, tom: User, applet_one_pending_subject: Subject
    ):
        client.login(tom)

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

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 2
        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one_with_flow.activities[0].id)
        assert assignment["respondentSubjectId"] == str(applet_one_pending_subject.id)
        assert assignment["targetSubjectId"] == str(applet_one_pending_subject.id)
        assert assignment["activityFlowId"] is None
        assert assignment["id"] is not None

    async def test_create_assignment_fail_wrong_respondent(
        self, client: TestClient, applet_one: AppletFull, tom: User, lucy: User, lucy_applet_two_subject: SubjectFull
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=lucy_applet_two_subject.id,
                    target_subject_id=lucy_applet_two_subject.id,
                )
            ]
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()
        result = response.json()["result"][0]
        assert (
            result["message"]
            == f"Invalid respondent subject id {lucy_applet_two_subject.id} for assignment to activity test"
        )

    async def test_create_assignment_fail_shell_account_respondent(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        lucy: User,
        tom_applet_one_subject: SubjectFull,
        applet_one_shell_account,
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=applet_one_shell_account.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()
        result = response.json()["result"][0]
        assert (
            result["message"]
            == f"Invalid respondent subject id {applet_one_shell_account.id} for assignment to activity test"
        )

    async def test_create_assignment_shell_account_target(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        lucy: User,
        tom_applet_one_subject: SubjectFull,
        applet_one_shell_account,
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=applet_one_shell_account.id,
                )
            ]
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one.activities[0].id)
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(applet_one_shell_account.id)
        assert assignment["activityFlowId"] is None
        assert assignment["id"] is not None

    async def test_create_assignment_fail_wrong_target(
        self, client: TestClient, applet_one: AppletFull, tom: User, tom_applet_one_subject: SubjectFull
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=uuid.UUID("7db2b7fe-3eba-4c70-8d02-dcf55b74d1c3"),
                )
            ]
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()
        result = response.json()["result"][0]
        assert (
            result["message"]
            == "Invalid target subject id 7db2b7fe-3eba-4c70-8d02-dcf55b74d1c3 for assignment to activity test"
        )

    async def test_create_multiple_assignments_duplicated(
        self,
        client: TestClient,
        applet_one_with_flow: AppletFull,
        tom: User,
        lucy_applet_one_subject: SubjectFull,
        tom_applet_one_subject: SubjectFull,
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one_with_flow.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                ),
            ]
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 1

        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one_with_flow.activities[0].id)
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["activityFlowId"] is None

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

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 1

        assignment = assignments[0]
        assert assignment["activityId"] is None
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(lucy_applet_one_subject.id)
        assert assignment["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)
