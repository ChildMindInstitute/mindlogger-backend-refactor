import http
import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from apps.activity_assignments.domain.assignments import ActivitiesAssignmentsCreate, ActivityAssignmentCreate
from apps.activity_flows.domain.flow_update import ActivityFlowItemUpdate, FlowUpdate
from apps.applets.domain.applet_create_update import AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.service import AppletService
from apps.shared.enums import Language
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import Subject, SubjectFull
from apps.users import User


@pytest.fixture
async def lucy_applet_one_subject(session: AsyncSession, lucy: User, applet_one_lucy_respondent: AppletFull) -> Subject:
    applet_id = applet_one_lucy_respondent.id
    user_id = lucy.id
    query = select(SubjectSchema).where(SubjectSchema.user_id == user_id, SubjectSchema.applet_id == applet_id)
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


class TestActivityAssignments(BaseTest):
    fixtures = [
        "activity_assignments/tests/fixtures/invitations.json",
    ]

    activities_assignments_applet = "/assignments/applet/{applet_id}"

    async def test_create_one_assignment(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        lucy_applet_one_subject: SubjectFull,
        session: AsyncSession,
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_id=tom.id,
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
        assert assignment["respondentId"] == str(tom.id)
        assert assignment["targetSubjectId"] == str(lucy_applet_one_subject.id)
        assert assignment["invitationId"] is None
        assert assignment["activityFlowId"] is None
        assert assignment["id"] is not None

        query = select(ActivityAssigmentSchema).where(ActivityAssigmentSchema.id == assignment["id"])
        res = await session.execute(query, execution_options={"synchronize_session": False})
        model = res.scalars().one()

        assert str(model.id) == assignment["id"]
        assert model.activity_id == applet_one.activities[0].id

    async def test_create_assignment_fail_wrong_activity(
        self, client: TestClient, applet_one: AppletFull, applet_two: AppletFull, tom: User
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(activity_id=applet_two.activities[0].id, respondent_id=tom.id)
            ]  # activity from applet two
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()
        result = response.json()["result"][0]
        assert result["message"] == f"Invalid activity id {applet_two.activities[0].id}"

    async def test_create_multiple_assignments_with_flow(
        self, client: TestClient, applet_one_with_flow: AppletFull, tom: User, lucy_applet_one_subject: SubjectFull
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(activity_id=applet_one_with_flow.activities[0].id, respondent_id=tom.id),
                ActivityAssignmentCreate(
                    activity_flow_id=applet_one_with_flow.activity_flows[0].id,
                    respondent_id=tom.id,
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
        assert assignment["respondentId"] == str(tom.id)
        assert assignment["targetSubjectId"] is None
        assert assignment["invitationId"] is None
        assert assignment["activityFlowId"] is None

        assignment = assignments[1]
        assert assignment["activityId"] is None
        assert assignment["respondentId"] == str(tom.id)
        assert assignment["targetSubjectId"] == str(lucy_applet_one_subject.id)
        assert assignment["invitationId"] is None
        assert assignment["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)

    async def test_create_assignment_fail_wrong_flow(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)

        fake_flow_id = uuid.uuid4()
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(activity_flow_id=fake_flow_id, respondent_id=tom.id)
            ]  # flow do not exists
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()
        result = response.json()["result"][0]
        assert result["message"] == f"Invalid flow id {fake_flow_id}"

    async def test_create_assignments_with_invitation(
        self,
        client: TestClient,
        applet_one_with_flow: AppletFull,
        tom: User,
        lucy_applet_one_subject: SubjectFull,
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one_with_flow.activities[0].id,
                    invitation_id=uuid.UUID("2ec0ea14-dd4b-41e9-814d-4360dde394e5"),
                    target_subject_id=lucy_applet_one_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_flow_id=applet_one_with_flow.activity_flows[0].id,
                    invitation_id=uuid.UUID("2ec0ea14-dd4b-41e9-814d-4360dde394e5"),
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
        assert assignment["respondentId"] is None
        assert assignment["targetSubjectId"] == str(lucy_applet_one_subject.id)
        assert assignment["invitationId"] == "2ec0ea14-dd4b-41e9-814d-4360dde394e5"
        assert assignment["activityFlowId"] is None
        assert assignment["id"] is not None

    async def test_create_assignment_fail_wrong_invitation(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    invitation_id=uuid.UUID("7db2b7fe-3eba-4c70-8d02-dcf55b74d1c3"),  # invitation for applet two
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
            == "Invalid invitation id 7db2b7fe-3eba-4c70-8d02-dcf55b74d1c3 for assignment to activity test"
        )

    async def test_create_assignment_fail_wrong_respondent(
        self, client: TestClient, applet_one: AppletFull, tom: User, lucy: User
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[ActivityAssignmentCreate(activity_id=applet_one.activities[0].id, respondent_id=lucy.id)]
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id), data=assignments_create
        )

        assert response.status_code == http.HTTPStatus.BAD_REQUEST, response.json()
        result = response.json()["result"][0]
        assert result["message"] == f"Invalid respondent id {lucy.id} for assignment to activity test"

    async def test_create_assignment_fail_wrong_target(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_id=tom.id,
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
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(activity_id=applet_one_with_flow.activities[0].id, respondent_id=tom.id),
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
        assert assignment["respondentId"] == str(tom.id)
        assert assignment["targetSubjectId"] is None
        assert assignment["invitationId"] is None
        assert assignment["activityFlowId"] is None

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(activity_id=applet_one_with_flow.activities[0].id, respondent_id=tom.id),
                ActivityAssignmentCreate(
                    activity_flow_id=applet_one_with_flow.activity_flows[0].id,
                    respondent_id=tom.id,
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
        assert assignment["respondentId"] == str(tom.id)
        assert assignment["targetSubjectId"] == str(lucy_applet_one_subject.id)
        assert assignment["invitationId"] is None
        assert assignment["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)
