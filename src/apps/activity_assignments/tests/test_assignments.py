import http
import re
import uuid

import pytest
from pydantic import EmailStr
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activity_assignments.db.schemas import ActivityAssigmentSchema
from apps.activity_assignments.domain.assignments import (
    ActivitiesAssignmentsCreate,
    ActivitiesAssignmentsDelete,
    ActivityAssignmentCreate,
    ActivityAssignmentDelete,
)
from apps.activity_flows.domain.flow_update import ActivityFlowItemUpdate, FlowUpdate
from apps.applets.domain.applet_create_update import AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.service import AppletService
from apps.invitations.domain import InvitationLanguage, InvitationRespondentRequest
from apps.mailing.services import TestMail
from apps.shared.enums import Language
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.crud import SubjectsCrud
from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import Subject, SubjectCreate, SubjectFull
from apps.subjects.services import SubjectsService
from apps.users import User


@pytest.fixture
def invitation_respondent_data(bill_bronson: User) -> InvitationRespondentRequest:
    return InvitationRespondentRequest(
        email=EmailStr(bill_bronson.email_encrypted),
        first_name=bill_bronson.first_name,
        last_name=bill_bronson.last_name,
        language=InvitationLanguage.EN,
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
async def applet_one_pending_invitation(client, tom: User, invitation_respondent_data, applet_one: AppletFull) -> dict:
    client.login(tom)
    response = await client.post(
        "/invitations/{applet_id}/respondent".format(applet_id=str(applet_one.id)),
        invitation_respondent_data.dict(),
    )
    assert response.status_code == http.HTTPStatus.OK
    data = response.json()["result"]
    return dict(key=data["key"], email=invitation_respondent_data.email)


@pytest.fixture
async def applet_one_pending_subject(
    applet_one_pending_invitation, applet_one: AppletFull, session: AsyncSession
) -> Subject:
    # invite a new respondent
    query = select(SubjectSchema).where(
        SubjectSchema.applet_id == applet_one.id, SubjectSchema.email == applet_one_pending_invitation["email"]
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


def message_language(message_body: str):
    assert message_body
    match_result = re.search(r"<span data-language=\"([^\"]*)\"></span>", message_body)
    assert match_result
    return match_result.group(1)


class TestActivityAssignments(BaseTest):
    activities_assignments_applet = "/assignments/applet/{applet_id}"
    user_activities_assignments = "/users/me/assignments/{applet_id}"
    activities_assign_unassign_applet = "/assignments/applet/{applet_id}"

    @pytest.mark.parametrize("invite_language", ["en", "fr", "el"])
    async def test_create_one_assignment(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        lucy_applet_one_subject: SubjectFull,
        tom_applet_one_subject,
        session: AsyncSession,
        mailbox: TestMail,
        invite_language: str,
    ):
        await SubjectsCrud(session).update(SubjectSchema(id=tom_applet_one_subject.id, language=invite_language))

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
        assert len(mailbox.mails) == 1

        query = select(ActivityAssigmentSchema).where(ActivityAssigmentSchema.id == assignment["id"])
        res = await session.execute(query, execution_options={"synchronize_session": False})
        model = res.scalars().one()

        assert str(model.id) == assignment["id"]
        assert model.activity_id == applet_one.activities[0].id
        assert mailbox.mails[0].recipients == [tom_applet_one_subject.email]
        assert message_language(mailbox.mails[0].body) == invite_language

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
        mailbox: TestMail,
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

        assert len(mailbox.mails) == 1
        assert mailbox.mails[0].recipients == [tom_applet_one_subject.email]
        assert mailbox.mails[0].subject == "Assignment Notification"

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
        self,
        client: TestClient,
        applet_one_with_flow: AppletFull,
        tom: User,
        applet_one_pending_subject: Subject,
        mailbox: TestMail,
        bill_bronson: User,
        applet_one_pending_invitation,
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
        assert len(mailbox.mails) == 0

        client.login(bill_bronson)
        url_accept = "/invitations/{key}/accept".format(key=applet_one_pending_invitation["key"])
        response = await client.post(url_accept)
        assert response.status_code == http.HTTPStatus.OK

        assert mailbox.mails[0].recipients == [applet_one_pending_invitation["email"]]
        assert mailbox.mails[0].subject == "Assignment Notification"

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
        mailbox: TestMail,
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
        assert len(mailbox.mails) == 1

        assert mailbox.mails[0].recipients == [tom_applet_one_subject.email]
        assert mailbox.mails[0].subject == "Assignment Notification"

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
        mailbox: TestMail,
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
        assert len(mailbox.mails) == 1
        assert mailbox.mails[0].recipients == [tom_applet_one_subject.email]
        assert mailbox.mails[0].subject == "Assignment Notification"

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
        assert len(mailbox.mails) == 2
        assert mailbox.mails[0].recipients == [tom_applet_one_subject.email]
        assert mailbox.mails[0].subject == "Assignment Notification"
        assert mailbox.mails[1].recipients == [tom_applet_one_subject.email]
        assert mailbox.mails[1].subject == "Assignment Notification"

    async def test_assignment_list_by_applet_success(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        lucy_applet_one_subject: SubjectFull,
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
        assignment_created = response.json()["result"]["assignments"][0]

        response = await client.get(self.activities_assignments_applet.format(applet_id=applet_one.id))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["result"]["appletId"] == str(applet_one.id)
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one.activities[0].id)
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(lucy_applet_one_subject.id)
        assert assignment["activityFlowId"] is None
        assert assignment["id"] == assignment_created["id"]

    async def test_assignment_list_by_applet_with_multiples_applets_success(
        self,
        client: TestClient,
        applet_one_with_flow: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        lucy_applet_two_subject: SubjectFull,
        applet_two_lucy_respondent: AppletFull,
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_flow_id=applet_one_with_flow.activity_flows[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id), data=assignments_create
        )
        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        assignment_one_created = response.json()["result"]["assignments"][0]

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_two_lucy_respondent.activities[0].id,
                    respondent_subject_id=lucy_applet_two_subject.id,
                    target_subject_id=lucy_applet_two_subject.id,
                )
            ]
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_two_lucy_respondent.id), data=assignments_create
        )
        assert response.status_code == http.HTTPStatus.CREATED, response.json()
        assignment_two_created = response.json()["result"]["assignments"][0]

        response = await client.get(self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["result"]["appletId"] == str(applet_one_with_flow.id)
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] is None
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)
        assert assignment["id"] == assignment_one_created["id"]

        response = await client.get(self.activities_assignments_applet.format(applet_id=applet_two_lucy_respondent.id))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["result"]["appletId"] == str(applet_two_lucy_respondent.id)
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_two_lucy_respondent.activities[0].id)
        assert assignment["respondentSubjectId"] == str(lucy_applet_two_subject.id)
        assert assignment["targetSubjectId"] == str(lucy_applet_two_subject.id)
        assert assignment["activityFlowId"] is None
        assert assignment["id"] == assignment_two_created["id"]

    async def test_assignment_list_by_applet_with_filtering(
        self,
        client: TestClient,
        applet_one_with_flow: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        lucy_applet_one_subject: SubjectFull,
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
        assignment_activity = [a for a in assignments if a["activityId"] == str(applet_one_with_flow.activities[0].id)][
            0
        ]
        assignment_flow = [
            a for a in assignments if a["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)
        ][0]

        url = self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id)
        url = url + "?activities=" + str(applet_one_with_flow.activities[0].id)
        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["result"]["appletId"] == str(applet_one_with_flow.id)
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one_with_flow.activities[0].id)
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["activityFlowId"] is None
        assert assignment["id"] == assignment_activity["id"]

        url = self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id)
        url = url + "?flows=" + str(applet_one_with_flow.activity_flows[0].id)
        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["result"]["appletId"] == str(applet_one_with_flow.id)
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] is None
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(lucy_applet_one_subject.id)
        assert assignment["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)
        assert assignment["id"] == assignment_flow["id"]

        url = self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id)
        url = (
            url
            + "?flows="
            + str(applet_one_with_flow.activity_flows[0].id)
            + "&activities="
            + str(applet_one_with_flow.activities[0].id)
        )
        response = await client.get(url)

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["result"]["appletId"] == str(applet_one_with_flow.id)
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 2

    async def test_assignment_list_by_applet_with_delete_subject(
        self,
        client: TestClient,
        applet_one_with_flow: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        lucy_applet_one_subject: SubjectFull,
        session: AsyncSession,
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
        assignment_activity = [a for a in assignments if a["activityId"] == str(applet_one_with_flow.activities[0].id)][
            0
        ]
        assignment_flow = [
            a for a in assignments if a["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)
        ][0]

        response = await client.get(self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["result"]["appletId"] == str(applet_one_with_flow.id)
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 2
        assignment = [a for a in assignments if a["activityId"] is not None][0]
        assert assignment["activityId"] == str(applet_one_with_flow.activities[0].id)
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["activityFlowId"] is None
        assert assignment["id"] == assignment_activity["id"]
        assignment = [a for a in assignments if a["activityFlowId"] is not None][0]
        assert assignment["activityId"] is None
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(lucy_applet_one_subject.id)
        assert assignment["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)
        assert assignment["id"] == assignment_flow["id"]

        assert lucy_applet_one_subject.id
        await SubjectsService(session, tom.id).delete(lucy_applet_one_subject.id)

        response = await client.get(self.activities_assignments_applet.format(applet_id=applet_one_with_flow.id))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["result"]["appletId"] == str(applet_one_with_flow.id)
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one_with_flow.activities[0].id)
        assert assignment["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment["activityFlowId"] is None
        assert assignment["id"] == assignment_activity["id"]

    async def test_assignment_list_by_respondent_success(
        self,
        client: TestClient,
        applet_one: AppletFull,
        tom: User,
        lucy: User,
        tom_applet_one_subject: Subject,
        lucy_applet_one_subject: Subject,
    ):
        client.login(tom)

        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=lucy_applet_one_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=applet_one.activities[0].id,
                    respondent_subject_id=lucy_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                ),
            ]
        )

        response = await client.post(
            self.activities_assignments_applet.format(applet_id=applet_one.id), data=assignments_create
        )
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        response = await client.get(self.user_activities_assignments.format(applet_id=applet_one.id))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["result"]["appletId"] == str(applet_one.id)
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one.activities[0].id)
        assert assignment["activityFlowId"] is None
        assert assignment["respondentSubject"]["id"] == str(tom_applet_one_subject.id)
        assert assignment["respondentSubject"]["firstName"] == tom_applet_one_subject.first_name
        assert assignment["respondentSubject"]["lastName"] == tom_applet_one_subject.last_name
        assert assignment["targetSubject"]["id"] == str(lucy_applet_one_subject.id)
        assert assignment["targetSubject"]["firstName"] == lucy_applet_one_subject.first_name
        assert assignment["targetSubject"]["lastName"] == lucy_applet_one_subject.last_name

        client.login(lucy)

        response = await client.get(self.user_activities_assignments.format(applet_id=applet_one.id))

        assert response.status_code == http.HTTPStatus.OK, response.json()
        assert response.json()["result"]["appletId"] == str(applet_one.id)
        assignments = response.json()["result"]["assignments"]
        assert len(assignments) == 1
        assignment = assignments[0]
        assert assignment["activityId"] == str(applet_one.activities[0].id)
        assert assignment["activityFlowId"] is None
        assert assignment["targetSubject"]["id"] == str(tom_applet_one_subject.id)
        assert assignment["targetSubject"]["firstName"] == tom_applet_one_subject.first_name
        assert assignment["targetSubject"]["lastName"] == tom_applet_one_subject.last_name
        assert assignment["respondentSubject"]["id"] == str(lucy_applet_one_subject.id)
        assert assignment["respondentSubject"]["firstName"] == lucy_applet_one_subject.first_name
        assert assignment["respondentSubject"]["lastName"] == lucy_applet_one_subject.last_name

    async def test_reassign_creation(
        self,
        client: TestClient,
        applet_one_with_flow: AppletFull,
        tom: User,
        lucy_applet_one_subject: SubjectFull,
        tom_applet_one_subject: SubjectFull,
        mailbox: TestMail,
    ):
        client.login(tom)

        assignments_create = dict(
            assignments=[
                dict(
                    activity_id=applet_one_with_flow.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                ),
                dict(
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
        assignment_activity_created = [
            a for a in assignments if a["activityId"] == str(applet_one_with_flow.activities[0].id)
        ][0]
        assignment_flow_created = [
            a for a in assignments if a["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)
        ][0]

        unassign_response = await client.delete(
            self.activities_assign_unassign_applet.format(applet_id=applet_one_with_flow.id),
            data=dict(
                assignments=[
                    dict(
                        activity_id=applet_one_with_flow.activities[0].id,
                        respondent_subject_id=tom_applet_one_subject.id,
                        target_subject_id=tom_applet_one_subject.id,
                    ),
                    dict(
                        activity_flow_id=applet_one_with_flow.activity_flows[0].id,
                        respondent_subject_id=tom_applet_one_subject.id,
                        target_subject_id=lucy_applet_one_subject.id,
                    ),
                ]
            ),
        )

        assert unassign_response.status_code == http.HTTPStatus.NO_CONTENT

        assignments_create = dict(
            assignments=[
                dict(
                    activity_id=applet_one_with_flow.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                ),
                dict(
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

        assignment_activity = [a for a in assignments if a["activityId"] == str(applet_one_with_flow.activities[0].id)][
            0
        ]
        assignment_flow = [
            a for a in assignments if a["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)
        ][0]

        assert assignment_activity["id"] == assignment_activity_created["id"]
        assert assignment_activity["activityId"] == str(applet_one_with_flow.activities[0].id)
        assert assignment_activity["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment_activity["targetSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment_activity["activityFlowId"] is None

        assert assignment_flow["id"] == assignment_flow_created["id"]
        assert assignment_flow["activityId"] is None
        assert assignment_flow["respondentSubjectId"] == str(tom_applet_one_subject.id)
        assert assignment_flow["targetSubjectId"] == str(lucy_applet_one_subject.id)
        assert assignment_flow["activityFlowId"] == str(applet_one_with_flow.activity_flows[0].id)

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
        activity_assignment_id = applet_one.activities[0].id
        subject_id = lucy_applet_one_subject.id
        target_id = tom_applet_one_subject.id
        # Use the same details as the existing assignment
        assignments_create = ActivitiesAssignmentsCreate(
            assignments=[
                ActivityAssignmentCreate(
                    activity_id=activity_assignment_id,
                    respondent_subject_id=subject_id,
                    target_subject_id=target_id,
                )
            ]
        )

        assignment_response = await client.post(
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignments_create,
        )

        assert assignment_response.status_code == http.HTTPStatus.CREATED, assignment_response.json()

        unassign_response = await client.delete(
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignments_create.dict(),
        )

        assert unassign_response.status_code == http.HTTPStatus.NO_CONTENT

        # Query based on activity_id, respondent_subject_id, and target_subject_id
        query = select(ActivityAssigmentSchema).where(
            ActivityAssigmentSchema.activity_id == activity_assignment_id,
            ActivityAssigmentSchema.respondent_subject_id == subject_id,
            ActivityAssigmentSchema.target_subject_id == target_id,
        )

        res = await session.execute(query)
        model = res.scalars().one()

        assert model.activity_id == activity_assignment_id
        assert model.respondent_subject_id == subject_id
        assert model.target_subject_id == target_id
        assert model.is_deleted is True

    async def test_unassign_no_effect_with_wrong_activity(
        self,
        client: TestClient,
        applet_one: AppletFull,
        applet_two: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        session: AsyncSession,
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
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignments_create,
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Step 2: Attempt to unassign it using the wrong applet_id (applet_one)
        assignment_delete = ActivitiesAssignmentsDelete(
            assignments=[
                ActivityAssignmentDelete(
                    activity_id=applet_two.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        response = await client.delete(
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignment_delete.dict(),
        )

        # Expect a 204 No Content because no assignments match the given applet_id
        assert response.status_code == http.HTTPStatus.NO_CONTENT

        # Verify that the assignment in applet_two still exists and is not marked as deleted
        query = select(ActivityAssigmentSchema).where(
            ActivityAssigmentSchema.activity_id == applet_one.activities[0].id,
            ActivityAssigmentSchema.respondent_subject_id == tom_applet_one_subject.id,
            ActivityAssigmentSchema.target_subject_id == tom_applet_one_subject.id,
        )
        res = await session.execute(query)
        assignment = res.scalars().first()

        assert assignment is not None  # The assignment should still exist
        assert assignment.is_deleted is False

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
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignments_create,
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Step 2: Attempt to unassign without providing activity_id or activity_flow_id
        assignment_delete = dict(
            assignments=[
                dict(
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        unassign_response = await client.delete(
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignment_delete,
        )

        # Expect a 400 Bad Request because neither activity_id nor activity_flow_id was provided
        assert unassign_response.status_code == http.HTTPStatus.BAD_REQUEST
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
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignments_create,
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Step 2: Attempt to unassign with both activity_id and activity_flow_id provided
        assignment_delete = dict(
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
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignment_delete,
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
            self.activities_assign_unassign_applet.format(applet_id=applet_one_with_flow.id),
            data=assignments_create,
        )

        assert assignment_response.status_code == http.HTTPStatus.CREATED, assignment_response.json()

        # Step 2: Unassign the previously assigned activities/flows
        assignment_delete = ActivitiesAssignmentsDelete(
            assignments=[
                ActivityAssignmentDelete(
                    activity_id=applet_one_with_flow.activities[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                ),
                ActivityAssignmentDelete(
                    activity_flow_id=applet_one_with_flow.activity_flows[0].id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=lucy_applet_one_subject.id,
                ),
            ]
        )

        unassign_response = await client.delete(
            self.activities_assign_unassign_applet.format(applet_id=applet_one_with_flow.id),
            data=assignment_delete.dict(),
        )

        assert unassign_response.status_code == http.HTTPStatus.NO_CONTENT, unassign_response.json()

        # Validate that the assignments have been unassigned
        for assignment in assignment_delete.assignments:
            query = select(ActivityAssigmentSchema).where(
                or_(
                    ActivityAssigmentSchema.activity_id == assignment.activity_id,
                    ActivityAssigmentSchema.activity_flow_id == assignment.activity_flow_id,
                ),
                ActivityAssigmentSchema.respondent_subject_id == assignment.respondent_subject_id,
                ActivityAssigmentSchema.target_subject_id == assignment.target_subject_id,
            )
            res = await session.execute(query)
            model = res.scalars().first()

            assert model is not None
            assert model.is_deleted is True

    async def test_unassign_no_effect_with_wrong_flow(
        self,
        client: TestClient,
        applet_one_with_flow: AppletFull,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        session: AsyncSession,
    ):
        client.login(tom)

        # Step 1: Assign an activity flow first
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
        response = await client.post(
            self.activities_assign_unassign_applet.format(applet_id=applet_one_with_flow.id),
            data=assignments_create,
        )

        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Step 2: Attempt to unassign it using a wrong flow_id from a different applet
        wrong_applet_id = uuid.UUID("7db2b7fe-3eba-4c70-8d02-dcf55b74d1c3")
        assignment_delete = ActivitiesAssignmentsDelete(
            assignments=[
                ActivityAssignmentDelete(
                    activity_flow_id=wrong_applet_id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        response = await client.delete(
            self.activities_assign_unassign_applet.format(applet_id=applet_one_with_flow.id),
            data=assignment_delete.dict(),
        )

        # Expect a 204 No Content because no assignments match the given flow_id
        assert response.status_code == http.HTTPStatus.NO_CONTENT

        # Verify that the assignment in applet_one_with_flow still exists and is not marked as deleted
        query = select(ActivityAssigmentSchema).where(
            ActivityAssigmentSchema.activity_flow_id == applet_one_with_flow.activity_flows[0].id,
            ActivityAssigmentSchema.respondent_subject_id == tom_applet_one_subject.id,
            ActivityAssigmentSchema.target_subject_id == tom_applet_one_subject.id,
        )
        res = await session.execute(query)
        assignment = res.scalars().first()

        assert assignment is not None  # The assignment should still exist
        assert assignment.is_deleted is False

    async def test_unassign_fail_missing_respondent(
        self,
        client: TestClient,
        applet_one: AppletFull,
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
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignments_create.dict(),
        )
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Step 2: Attempt to unassign without providing target_subject_id using a dictionary
        assignment_delete = {
            "assignments": [
                {
                    "activity_id": str(applet_one.activities[0].id),
                    "respondent_subject_id": str(tom_applet_one_subject.id),
                    "target_subject_id": None,  # Missing target_subject_id
                }
            ]
        }

        unassign_response = await client.delete(
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignment_delete,
        )

        # Expect a 400 Bad Request due to missing target_subject_id
        assert unassign_response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY

    async def test_unassign_fail_missing_target(
        self,
        client: TestClient,
        applet_one: AppletFull,
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
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignments_create.dict(),
        )
        assert response.status_code == http.HTTPStatus.CREATED, response.json()

        # Step 2: Attempt to unassign without providing target_subject_id using a dictionary
        assignment_delete = {
            "assignments": [
                {
                    "activity_id": str(applet_one.activities[0].id),
                    "respondent_subject_id": str(tom_applet_one_subject.id),
                    "target_subject_id": None,  # Missing target_subject_id
                }
            ]
        }

        unassign_response = await client.delete(
            self.activities_assign_unassign_applet.format(applet_id=applet_one.id),
            data=assignment_delete,  # Use json= to pass the dictionary as JSON
        )

        # Expect a 400 Bad Request due to missing target_subject_id
        assert unassign_response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
