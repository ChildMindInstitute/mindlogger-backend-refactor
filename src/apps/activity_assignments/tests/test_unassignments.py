import http
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
async def applet_two_with_flow(
    session: AsyncSession,
    applet_two: AppletFull,
    applet_minimal_data: AppletFull,
    tom: User,
):
    data = AppletUpdate(**applet_minimal_data.dict())
    flow = FlowUpdate(
        name="flow_two",
        items=[ActivityFlowItemUpdate(id=None, activity_key=data.activities[0].key)],
        description={Language.ENGLISH: "description for flow two"},
        id=None,
    )
    data.activity_flows = [flow]
    srv = AppletService(session, tom.id)
    await srv.update(applet_two.id, data)
    applet = await srv.get_full_applet(applet_two.id)
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
    activities_assign_unassign_applet = "/assignments/applet/{applet_id}"

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
        assert result["message"] == "Either activity_id or activity_flow_id must be provided, but not both"

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
        wrong_applet_id = "7db2b7fe-3eba-4c70-8d02-dcf55b74d1c3"
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
        assert unassign_response.status_code == http.HTTPStatus.BAD_REQUEST
        result = unassign_response.json()["result"][0]
        assert result["message"] == "Target subject ID must be provided"

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
        assert unassign_response.status_code == http.HTTPStatus.BAD_REQUEST
        result = unassign_response.json()["result"][0]
        assert result["message"] == "Target subject ID must be provided"
