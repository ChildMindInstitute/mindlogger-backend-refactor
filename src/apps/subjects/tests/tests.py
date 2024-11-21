import http
import json
import uuid
from copy import copy
from datetime import datetime, timedelta

import pytest
from asyncpg import UniqueViolationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.activity_update import ActivityUpdate
from apps.activities.services.activity import ActivityService
from apps.activity_assignments.domain.assignments import ActivityAssignmentCreate, ActivityAssignmentDelete
from apps.activity_assignments.service import ActivityAssignmentService
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.domain import AppletAnswerCreate
from apps.answers.service import AnswerService
from apps.applets.domain.applet_full import AppletFull
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.crud import SubjectsCrud
from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import Subject, SubjectCreate, SubjectCreateRequest, SubjectRelationCreate
from apps.subjects.services import SubjectsService
from apps.users import User
from apps.users.domain import UserCreate
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


@pytest.fixture
def create_shell_body(applet_one):
    return SubjectCreateRequest(
        applet_id=str(applet_one.id),
        language="en",
        first_name="fn",
        last_name="ln",
        secret_user_id="1234",
        tag="tag1234",
    ).dict()


@pytest.fixture
def subject_schema():
    return SubjectCreate(
        applet_id=uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b1"),
        email="subject@mail.com",
        creator_id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa1"),
        user_id=uuid.UUID("6a180cd9-db2b-4195-a5ac-30a8733dfb06"),
        language="en",
        first_name="first_name",
        last_name="last_name",
        secret_user_id="secret_user_id",
        nickname="nickname",
        tag="tag",
    )


@pytest.fixture
def subject_updated_schema(subject_schema):
    return SubjectCreate(
        applet_id=subject_schema.applet_id,
        email=f"new-{subject_schema.email}",
        creator_id=subject_schema.user_id,
        user_id=subject_schema.user_id,
        language="en",
        first_name=f"new-{subject_schema.first_name}",
        last_name=f"new-{subject_schema.last_name}",
        secret_user_id=f"new-{subject_schema.secret_user_id}",
        nickname=f"new-{subject_schema.nickname}",
        tag=f"new-{subject_schema.tag}",
    )


@pytest.fixture
def answer_create_payload(applet_one: AppletFull):
    return dict(
        submit_id=str(uuid.uuid4()),
        applet_id=str(applet_one.id),
        activity_id=str(applet_one.activities[0].id),
        version=applet_one.version,
        created_at=1690188731636,
        answer=dict(
            user_public_key="user key",
            answer=json.dumps(
                dict(
                    value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                    additional_text=None,
                )
            ),
            events=json.dumps(dict(events=["event1", "event2"])),
            item_ids=[
                str(applet_one.activities[0].items[0].id),
            ],
            identifier="encrypted_identifier",
            scheduled_time=1690188679657,
            start_time=1690188679657,
            end_time=1690188731636,
            scheduledEventId="eventId",
            localEndDate="2022-10-01",
            localEndTime="12:35:00",
        ),
        alerts=[
            dict(
                activity_item_id=str(applet_one.activities[0].items[0].id),
                message="hello world",
            )
        ],
        client=dict(
            appId="mindlogger-mobile",
            appVersion="0.21.48",
            width=819,
            height=1080,
        ),
    )


@pytest.fixture
def answer_create_arbitrary_payload():
    return dict(
        submit_id="270d86e0-2158-4d18-befd-86b3ce0122a1",
        applet_id="92917a56-d586-4613-b7aa-991f2c4b15b8",
        activity_id="cca523e4-ab59-4bbc-a0b8-5fcb2cdda58d",
        version="1.1.0",
        created_at=1690188731636,
        answer=dict(
            user_public_key="user key",
            answer=json.dumps(
                dict(
                    value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                    additional_text=None,
                )
            ),
            events=json.dumps(dict(events=["event1", "event2"])),
            item_ids=[
                "a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                "a18d3409-2c96-4a5e-a1f3-1c1c14be0014",
            ],
            identifier="encrypted_identifier",
            scheduled_time=1690188679657,
            start_time=1690188679657,
            end_time=1690188731636,
        ),
        alerts=[
            dict(
                activity_item_id="a18d3409-2c96-4a5e-a1f3-1c1c14be0011",
                message="hello world",
            )
        ],
        client=dict(
            appId="mindlogger-mobile",
            appVersion="0.21.48",
            width=819,
            height=1080,
        ),
    )


@pytest.fixture(params=range(4))
async def update_subject_params(request, tom_applet_one_subject):
    params = (
        (
            # Duplicated secret id
            dict(secretUserId=tom_applet_one_subject.secret_user_id),
            http.HTTPStatus.BAD_REQUEST,
        ),
        (dict(secretUserId=str(uuid.uuid4())), http.HTTPStatus.OK),
        (
            dict(secretUserId=str(uuid.uuid4()), nickname="bob", tag="tagUpdated"),
            http.HTTPStatus.OK,
        ),
        (dict(nickname="bob"), http.HTTPStatus.UNPROCESSABLE_ENTITY),
    )
    body, expected_status = params[request.param]
    return body, expected_status


@pytest.fixture
async def applet_one_lucy_manager(session: AsyncSession, applet_one: AppletFull, tom, lucy) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.MANAGER)
    return applet_one


@pytest.fixture
async def applet_one_bob_coordinator(session: AsyncSession, applet_one: AppletFull, tom, bob) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(bob.id, Role.COORDINATOR)
    return applet_one


@pytest.fixture
async def applet_one_pit_editor(session: AsyncSession, applet_one: AppletFull, tom, pit) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(pit.id, Role.EDITOR)
    return applet_one


@pytest.fixture
async def applet_one_pit_reviewer(session: AsyncSession, applet_one: AppletFull, tom, pit) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(pit.id, Role.REVIEWER)
    return applet_one


@pytest.fixture
async def applet_one_lucy_respondent(session: AsyncSession, applet_one: AppletFull, tom, lucy) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.RESPONDENT)
    return applet_one


@pytest.fixture
async def applet_one_pit_respondent(session: AsyncSession, applet_one: AppletFull, tom: User, pit: User) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(pit.id, Role.RESPONDENT)
    return applet_one


@pytest.fixture
async def lucy_applet_one_subject(session: AsyncSession, lucy: User, applet_one_lucy_respondent: AppletFull) -> Subject:
    applet_id = applet_one_lucy_respondent.id
    user_id = lucy.id
    query = select(SubjectSchema).where(SubjectSchema.user_id == user_id, SubjectSchema.applet_id == applet_id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
async def pit_applet_one_subject(session: AsyncSession, pit: User, applet_one_pit_respondent: AppletFull) -> Subject:
    applet_id = applet_one_pit_respondent.id
    user_id = pit.id
    query = select(SubjectSchema).where(SubjectSchema.user_id == user_id, SubjectSchema.applet_id == applet_id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
async def applet_one_lucy_reviewer_with_subject(
    session: AsyncSession, applet_one: AppletFull, tom_applet_one_subject, tom, lucy
) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(
        lucy.id, Role.REVIEWER, {"subjects": [str(tom_applet_one_subject.id)]}
    )
    return applet_one


@pytest.fixture
async def tom_invitation_payload(tom: User) -> dict:
    return dict(
        email=tom.email_encrypted, first_name=tom.first_name, last_name=tom.last_name, language="en", role=Role.MANAGER
    )


@pytest.fixture
async def lucy_participant_invitation_payload(lucy: User) -> dict:
    return dict(
        email=lucy.email_encrypted,
        first_name=lucy.first_name,
        last_name=lucy.last_name,
        language="en",
        role=Role.RESPONDENT,
    )


@pytest.fixture
async def applet_one_shell_account(session: AsyncSession, applet_one: AppletFull, tom: User) -> Subject:
    return await SubjectsService(session, tom.id).create(
        SubjectCreate(
            applet_id=applet_one.id,
            creator_id=tom.id,
            first_name="Shell",
            last_name="Account",
            nickname="shell-account-0",
            secret_user_id=f"{uuid.uuid4()}",
            email="shell@mail.com",
        )
    )


class TestSubjects(BaseTest):
    fixtures = [
        "workspaces/fixtures/workspaces.json",
    ]

    login_url = "/auth/login"
    subject_list_url = "/subjects"
    my_subject_url = "/users/me/subjects/{applet_id}"
    subject_detail_url = "/subjects/{subject_id}"
    subject_relation_url = "/subjects/{subject_id}/relations/{source_subject_id}"
    subject_temporary_multiinformant_relation_url = (
        "/subjects/{subject_id}/relations/{source_subject_id}/multiinformant-assessment"
    )
    subject_target_by_respondent_url = (
        "/subjects/respondent/{respondent_subject_id}/activity-or-flow/{activity_or_flow_id}"
    )
    answer_url = "/answers"

    async def test_create_subject(self, client, tom: User, applet_one: AppletFull, create_shell_body):
        creator_id = str(tom.id)
        applet_id = str(applet_one.id)
        client.login(tom)
        response = await client.post(self.subject_list_url, data=create_shell_body)
        assert response.status_code == 201
        payload = response.json()
        assert payload
        assert payload["result"]["appletId"] == applet_id
        assert payload["result"]["email"] is None
        assert payload["result"]["creatorId"] == creator_id
        assert payload["result"]["userId"] is None
        assert payload["result"]["language"] == "en"
        assert payload["result"]["tag"] == create_shell_body["tag"]

    async def test_create_relation(self, client, tom: User, create_shell_body, tom_applet_one_subject):
        subject_id = tom_applet_one_subject.id
        client.login(tom)
        response = await client.post(self.subject_list_url, data=create_shell_body)
        subject = response.json()

        source_subject_id = str(subject_id)
        target_subject_id = subject["result"]["id"]

        body = SubjectRelationCreate(
            relation="father",
        )
        url = self.subject_relation_url.format(subject_id=target_subject_id, source_subject_id=source_subject_id)
        res = await client.post(url, body)
        assert res.status_code == http.HTTPStatus.OK

    async def test_create_temporary_multiinformant_relation(
        self, client, tom: User, create_shell_body, tom_applet_one_subject
    ):
        subject_id = tom_applet_one_subject.id
        client.login(tom)
        response = await client.post(self.subject_list_url, data=create_shell_body)
        subject = response.json()

        source_subject_id = str(subject_id)
        target_subject_id = subject["result"]["id"]

        url = self.subject_temporary_multiinformant_relation_url.format(
            subject_id=target_subject_id, source_subject_id=source_subject_id
        )
        res = await client.post(url)
        assert res.status_code == http.HTTPStatus.OK

    async def test_recreate_temporary_multiinformant_relation(
        self, client, tom: User, create_shell_body, tom_applet_one_subject
    ):
        subject_id = tom_applet_one_subject.id
        client.login(tom)
        response = await client.post(self.subject_list_url, data=create_shell_body)
        subject = response.json()

        source_subject_id = str(subject_id)
        target_subject_id = subject["result"]["id"]

        url = self.subject_temporary_multiinformant_relation_url.format(
            subject_id=target_subject_id, source_subject_id=source_subject_id
        )
        res = await client.post(url)
        assert res.status_code == http.HTTPStatus.OK

        # This endpoint should be idempotent
        res = await client.post(url)
        assert res.status_code == http.HTTPStatus.OK

    async def test_create_temporary_multiinformant_relation_no_op(
        self, client, tom: User, create_shell_body, tom_applet_one_subject
    ):
        subject_id = tom_applet_one_subject.id
        client.login(tom)
        response = await client.post(self.subject_list_url, data=create_shell_body)
        subject = response.json()

        source_subject_id = str(subject_id)
        target_subject_id = subject["result"]["id"]

        body = SubjectRelationCreate(
            relation="father",
        )
        url = self.subject_relation_url.format(subject_id=target_subject_id, source_subject_id=source_subject_id)
        res = await client.post(url, body)
        assert res.status_code == http.HTTPStatus.OK

        # Creating a temporary relation at this point should be a no-op
        url = self.subject_temporary_multiinformant_relation_url.format(
            subject_id=target_subject_id, source_subject_id=source_subject_id
        )
        res = await client.post(url)
        assert res.status_code == http.HTTPStatus.OK

    @pytest.mark.parametrize(
        "subject_id,source_subject_id,exp_code",
        (
            (uuid.uuid4(), None, http.HTTPStatus.NOT_FOUND),
            (None, uuid.uuid4(), http.HTTPStatus.NOT_FOUND),
            (None, None, http.HTTPStatus.OK),
        ),
    )
    async def test_remove_relation(
        self,
        client,
        tom: User,
        create_shell_body,
        subject_id,
        source_subject_id,
        exp_code,
    ):
        client.login(tom)
        response = await client.post(self.subject_list_url, data=create_shell_body)
        source_subject = response.json()
        _source_subject_id = source_subject["result"]["id"]

        payload = copy(create_shell_body)
        payload.update(
            {
                "firstName": "first2",
                "lastName": "last2",
                "secretUserId": "secret2",
            }
        )
        response = await client.post(self.subject_list_url, data=payload)
        target_subject = response.json()
        _target_subject_id = target_subject["result"]["id"]

        body = SubjectRelationCreate(
            relation="father",
        )
        url = self.subject_relation_url.format(subject_id=_target_subject_id, source_subject_id=_source_subject_id)
        await client.post(url, body.dict())

        url_delete = self.subject_relation_url.format(
            subject_id=subject_id if subject_id else _target_subject_id,
            source_subject_id=source_subject_id if source_subject_id else _source_subject_id,
        )
        res = await client.delete(url_delete)
        assert res.status_code == exp_code

    async def test_update_subject(self, client, session, tom: User, create_shell_body, update_subject_params):
        body, exp_status = update_subject_params
        client.login(tom)
        response = await client.post(self.subject_list_url, data=create_shell_body)
        subject = response.json()["result"]
        url = self.subject_detail_url.format(subject_id=subject["id"])
        response = await client.put(url, body)
        assert response.status_code == exp_status
        payload = response.json()
        assert payload
        subject = await SubjectsCrud(session).get_by_id(subject["id"])
        if exp_status == http.HTTPStatus.OK:
            exp_secret_id = body.get("secretUserId")
            exp_nickname = body.get("nickname")
            exp_tag = body.get("tag")
        else:
            exp_secret_id = create_shell_body.get("secret_user_id")
            exp_nickname = create_shell_body.get("nickname")
            exp_tag = create_shell_body.get("tag")

        assert subject.secret_user_id == exp_secret_id
        assert subject.nickname == exp_nickname
        assert subject.tag == exp_tag

    async def test_upsert_for_soft_deleted(self, session: AsyncSession, subject_schema, subject_updated_schema):
        service = SubjectsService(session, subject_schema.user_id)
        original_subject = await service.create(subject_schema)
        assert original_subject.id
        await service.delete(original_subject.id)
        result_subject = await service.create(subject_updated_schema)
        assert result_subject.id
        actual_subject = await service.get(result_subject.id)
        assert actual_subject
        for field_name in SubjectCreate.__fields__.keys():
            actual = getattr(actual_subject, field_name)
            expected = getattr(result_subject, field_name)
            assert actual == expected

    async def test_upsert_subject_fail_for_not_soft_deleted(
        self, session: AsyncSession, subject_schema, subject_updated_schema
    ):
        service = SubjectsService(session, subject_schema.user_id)
        original_subject = await service.create(subject_schema)
        try:
            await service.create(subject_updated_schema)
        except UniqueViolationError:
            pass

        assert original_subject.id
        actual_subject = await service.get(original_subject.id)
        assert actual_subject
        for field_name in SubjectCreate.__fields__.keys():
            actual = getattr(actual_subject, field_name)
            expected = getattr(original_subject, field_name)
            assert actual == expected

    async def test_successfully_delete_subject_without_answers(
        self, session, client, tom: User, tom_applet_one_subject, answer_create_payload, mock_kiq_report
    ):
        subject_id = tom_applet_one_subject.id
        client.login(tom)
        response = await client.post(self.answer_url, data=answer_create_payload)

        assert response.status_code == http.HTTPStatus.CREATED
        delete_url = self.subject_detail_url.format(subject_id=subject_id)
        res = await client.delete(delete_url, data=dict(deleteAnswers=False))
        assert res.status_code == http.HTTPStatus.OK

        subject = await SubjectsCrud(session).get_by_id(subject_id)
        assert subject
        assert subject.soft_exists(False)
        count = await AnswersCRUD(session).count(target_subject_id=subject_id)
        assert count

    async def test_successfully_delete_subject_with_answers(
        self, session, client, tom: User, tom_applet_one_subject, answer_create_payload, mock_kiq_report
    ):
        subject_id = tom_applet_one_subject.id
        client.login(tom)
        response = await client.post(self.answer_url, data=answer_create_payload)

        assert response.status_code == http.HTTPStatus.CREATED
        delete_url = self.subject_detail_url.format(subject_id=subject_id)
        res = await client.delete(delete_url, data=dict(deleteAnswers=True))
        assert res.status_code == http.HTTPStatus.OK
        subject = await SubjectsCrud(session).get_by_id(subject_id)
        assert not subject
        count = await AnswersCRUD(session).count(target_subject_id=subject_id)
        assert count == 0

    @pytest.mark.parametrize(
        "user_fixture,expected",
        (
            # Owner
            ("tom", http.HTTPStatus.OK),
            # Manager
            ("lucy", http.HTTPStatus.OK),
            # Coordinator
            ("bob", http.HTTPStatus.OK),
            # Editor, reviewer
            ("pit", http.HTTPStatus.FORBIDDEN),
        ),
    )
    async def test_error_try_delete_subject_by_not_owner(
        self,
        session,
        client,
        tom_applet_one_subject,
        applet_one_lucy_manager,
        applet_one_bob_coordinator,
        applet_one_pit_editor,
        applet_one_pit_reviewer,
        request,
        user_fixture,
        expected,
    ):
        subject_id = tom_applet_one_subject.id
        client.login(request.getfixturevalue(user_fixture))
        delete_url = self.subject_detail_url.format(subject_id=subject_id)
        res = await client.delete(delete_url, data=dict(deleteAnswers=True))
        assert res.status_code == expected

    async def test_get_subject_full(self, client, tom: User, tom_applet_one_subject: Subject, lucy, lucy_create):
        subject_id = tom_applet_one_subject.id
        client.login(tom)
        response = await client.get(self.subject_detail_url.format(subject_id=subject_id))
        assert response.status_code == http.HTTPStatus.OK
        data = response.json()
        assert data
        res = data["result"]
        assert set(res.keys()) == {
            "id",
            "secretUserId",
            "nickname",
            "lastSeen",
            "tag",
            "appletId",
            "firstName",
            "lastName",
            "userId",
        }
        assert uuid.UUID(res["id"]) == tom_applet_one_subject.id
        assert res["secretUserId"] == tom_applet_one_subject.secret_user_id
        assert res["nickname"] == tom_applet_one_subject.nickname
        assert res["tag"] == tom_applet_one_subject.tag
        assert uuid.UUID(res["appletId"]) == tom_applet_one_subject.applet_id
        assert uuid.UUID(res["userId"]) == tom.id

        # not found
        response = await client.get(self.subject_detail_url.format(subject_id=uuid.uuid4()))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

        # forbidden
        client.login(lucy)
        response = await client.get(self.subject_detail_url.format(subject_id=subject_id))
        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_get_subject_related_participant(
        self,
        session: AsyncSession,
        client: TestClient,
        tom: User,
        lucy: User,
        tom_applet_one_subject: Subject,
        lucy_applet_one_subject: Subject,
        applet_one_shell_account: Subject,
    ):
        client.login(lucy)
        response = await client.get(self.subject_detail_url.format(subject_id=applet_one_shell_account.id))
        assert response.status_code == http.HTTPStatus.FORBIDDEN

        await SubjectsService(session, tom.id).create_relation(
            applet_one_shell_account.id, lucy_applet_one_subject.id, "parent"
        )

        response = await client.get(self.subject_detail_url.format(subject_id=applet_one_shell_account.id))
        assert response.status_code == http.HTTPStatus.OK

    async def test_get_subject_temp_related_participant(
        self,
        session: AsyncSession,
        client: TestClient,
        tom: User,
        lucy: User,
        tom_applet_one_subject: Subject,
        lucy_applet_one_subject: Subject,
        applet_one_shell_account: Subject,
    ):
        client.login(lucy)
        response = await client.get(self.subject_detail_url.format(subject_id=applet_one_shell_account.id))
        assert response.status_code == http.HTTPStatus.FORBIDDEN

        # Expires tomorrow
        expires_at = datetime.now() + timedelta(days=1)
        await SubjectsService(session, tom.id).create_relation(
            applet_one_shell_account.id, lucy_applet_one_subject.id, "take-now", {"expiresAt": expires_at.isoformat()}
        )

        response = await client.get(self.subject_detail_url.format(subject_id=applet_one_shell_account.id))
        assert response.status_code == http.HTTPStatus.OK

    async def test_get_subject_expired_temp_related_participant(
        self,
        session: AsyncSession,
        client: TestClient,
        tom: User,
        lucy: User,
        tom_applet_one_subject: Subject,
        lucy_applet_one_subject: Subject,
        applet_one_shell_account: Subject,
    ):
        client.login(lucy)
        response = await client.get(self.subject_detail_url.format(subject_id=applet_one_shell_account.id))
        assert response.status_code == http.HTTPStatus.FORBIDDEN

        # Expired yesterday
        expires_at = datetime.now() - timedelta(days=1)
        await SubjectsService(session, tom.id).create_relation(
            applet_one_shell_account.id, lucy_applet_one_subject.id, "take-now", {"expiresAt": expires_at.isoformat()}
        )

        response = await client.get(self.subject_detail_url.format(subject_id=applet_one_shell_account.id))
        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_get_my_subject(self, client, tom: User, tom_applet_one_subject: Subject):
        client.login(tom)
        response = await client.get(self.my_subject_url.format(applet_id=tom_applet_one_subject.applet_id))
        assert response.status_code == http.HTTPStatus.OK
        data = response.json()
        assert data
        res = data["result"]
        assert set(res.keys()) == {
            "id",
            "secretUserId",
            "nickname",
            "lastSeen",
            "tag",
            "appletId",
            "firstName",
            "lastName",
            "userId",
        }
        assert uuid.UUID(res["id"]) == tom_applet_one_subject.id
        assert res["secretUserId"] == tom_applet_one_subject.secret_user_id
        assert res["nickname"] == tom_applet_one_subject.nickname
        assert res["tag"] == tom_applet_one_subject.tag
        assert uuid.UUID(res["appletId"]) == tom_applet_one_subject.applet_id
        assert uuid.UUID(res["userId"]) == tom.id

    async def test_get_my_subject_invalid_applet_id(self, client, tom: User):
        client.login(tom)
        response = await client.get(self.my_subject_url.format(applet_id=uuid.uuid4()))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_get_subject_limited(
        self,
        client,
        applet_one_shell_account: Subject,
        tom: User,
    ):
        subject_id = applet_one_shell_account.id
        client.login(tom)
        response = await client.get(self.subject_detail_url.format(subject_id=subject_id))
        assert response.status_code == http.HTTPStatus.OK
        data = response.json()
        assert data
        res = data["result"]
        assert set(res.keys()) == {
            "id",
            "secretUserId",
            "nickname",
            "lastSeen",
            "tag",
            "appletId",
            "firstName",
            "lastName",
            "userId",
        }
        assert uuid.UUID(res["id"]) == applet_one_shell_account.id
        assert res["secretUserId"] == applet_one_shell_account.secret_user_id
        assert res["nickname"] == applet_one_shell_account.nickname
        assert res["tag"] == applet_one_shell_account.tag
        assert uuid.UUID(res["appletId"]) == applet_one_shell_account.applet_id
        assert res["userId"] is None

    async def test_get_reviewer_subject(
        self,
        client,
        tom_applet_one_subject,
        pit_create: UserCreate,
        pit,
        applet_one_pit_reviewer,
        lucy_create,
        lucy,
        applet_one_lucy_reviewer_with_subject,
    ):
        subject_id = tom_applet_one_subject.id
        # forbidden for reviewer without subject assigned
        client.login(pit)
        response = await client.get(self.subject_detail_url.format(subject_id=subject_id))
        assert response.status_code == http.HTTPStatus.FORBIDDEN

        # allowed for reviewer with subject assigned
        client.login(lucy)
        response = await client.get(self.subject_detail_url.format(subject_id=subject_id))
        assert response.status_code == http.HTTPStatus.OK
        data = response.json()
        assert data

    async def test_editor_remove_respondent_access_error(
        self, client, session, tom, mike, lucy, applet_one: AppletFull, applet_one_lucy_respondent
    ):
        roles_to_delete = [Role.OWNER, Role.COORDINATOR, Role.MANAGER, Role.SUPER_ADMIN, Role.REVIEWER]
        await UserAppletAccessCRUD(session).delete_user_roles(applet_one.id, mike.id, roles_to_delete)
        client.login(mike)
        subject = await SubjectsService(session, tom.id).get_by_user_and_applet(lucy.id, applet_one.id)
        assert subject
        delete_url = self.subject_detail_url.format(subject_id=subject.id)
        response = await client.delete(delete_url, data=dict(deleteAnswers=False))
        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_workspace_coordinator_remove_respondent_access(
        self, client, session, lucy, applet_one, user, applet_one_bob_coordinator, applet_one_lucy_respondent, bob, tom
    ):
        client.login(bob)
        subject = await SubjectsService(session, tom.id).get_by_user_and_applet(lucy.id, applet_one.id)
        assert subject
        delete_url = self.subject_detail_url.format(subject_id=subject.id)
        response = await client.delete(delete_url, data=dict(deleteAnswers=False))
        assert response.status_code == http.HTTPStatus.OK

    @pytest.mark.parametrize(
        "user_fixture,expected",
        (
            # Owner
            ("tom", http.HTTPStatus.OK),
            # Manager
            ("lucy", http.HTTPStatus.OK),
            # Coordinator
            ("bob", http.HTTPStatus.OK),
            # Editor
            ("pit", http.HTTPStatus.FORBIDDEN),
        ),
    )
    async def test_error_try_get_subject_by_not_inviter(
        self,
        session,
        client,
        tom_applet_one_subject,
        applet_one_lucy_manager,
        applet_one_bob_coordinator,
        applet_one_pit_editor,
        request,
        user_fixture,
        expected,
    ):
        subject_id = tom_applet_one_subject.id
        client.login(request.getfixturevalue(user_fixture))
        res = await client.get(self.subject_detail_url.format(subject_id=subject_id))
        assert res.status_code == expected

    async def test_get_target_subjects_by_respondent_invalid_respondent(
        self, client, tom: User, applet_one: AppletFull
    ):
        invalid_respondent_subject_id = str(uuid.uuid4())
        activity_or_flow_id = str(applet_one.activities[0].id)
        client.login(tom)
        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=invalid_respondent_subject_id, activity_or_flow_id=activity_or_flow_id
        )
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_get_target_subjects_by_respondent_limited_account_respondent(
        self, client, tom: User, applet_one: AppletFull, applet_one_shell_account: Subject
    ):
        activity_or_flow_id = str(applet_one.activities[0].id)
        client.login(tom)
        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=applet_one_shell_account.id, activity_or_flow_id=activity_or_flow_id
        )
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.OK

    async def test_get_target_subjects_by_respondent_editor_user(
        self, client, applet_one_pit_editor: AppletFull, pit: User, tom_applet_one_subject: Subject
    ):
        activity_or_flow_id = str(applet_one_pit_editor.activities[0].id)
        client.login(pit)
        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=tom_applet_one_subject.id, activity_or_flow_id=activity_or_flow_id
        )
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_get_target_subjects_by_respondent_respondent_user(
        self, client, lucy: User, tom_applet_one_subject: Subject, applet_one_lucy_respondent: AppletFull
    ):
        activity_or_flow_id = str(applet_one_lucy_respondent.activities[0].id)
        client.login(lucy)
        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=tom_applet_one_subject.id, activity_or_flow_id=activity_or_flow_id
        )
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_get_target_subjects_by_respondent_reviewer_without_assignment(
        self, client, lucy: User, tom_applet_one_subject: Subject, applet_one_pit_reviewer: AppletFull
    ):
        activity_or_flow_id = str(applet_one_pit_reviewer.activities[0].id)
        client.login(lucy)
        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=tom_applet_one_subject.id, activity_or_flow_id=activity_or_flow_id
        )
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_get_target_subjects_by_respondent_reviewer_with_assignment(
        self, client, lucy: User, tom_applet_one_subject: Subject, applet_one_lucy_reviewer_with_subject: AppletFull
    ):
        activity_or_flow_id = str(applet_one_lucy_reviewer_with_subject.activities[0].id)
        client.login(lucy)
        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=tom_applet_one_subject.id, activity_or_flow_id=activity_or_flow_id
        )
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.OK

    async def test_get_target_subjects_by_respondent_no_assignments_or_submissions(
        self,
        client,
        tom: User,
        tom_applet_one_subject: Subject,
        lucy_applet_one_subject: Subject,
        applet_one_lucy_respondent: AppletFull,
        session,
    ):
        activity_or_flow_id = str(applet_one_lucy_respondent.activities[0].id)
        client.login(tom)

        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=lucy_applet_one_subject.id, activity_or_flow_id=activity_or_flow_id
        )
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.OK

        result = response.json()["result"]

        assert len(result) == 1

        subject_result = result[0]

        assert subject_result["id"] == str(lucy_applet_one_subject.id)
        assert subject_result["submissionCount"] == 0
        assert subject_result["currentlyAssigned"] is True

    async def test_get_target_subjects_by_respondent_manual_assignment(
        self,
        client,
        tom: User,
        tom_applet_one_subject: Subject,
        lucy_applet_one_subject: Subject,
        applet_one_lucy_respondent: AppletFull,
        session,
    ):
        activity = applet_one_lucy_respondent.activities[0]

        # Turn off auto-assignment
        activity_service = ActivityService(session, tom.id)
        await activity_service.remove_applet_activities(applet_one_lucy_respondent.id)
        await activity_service.update_create(
            applet_one_lucy_respondent.id,
            [
                ActivityUpdate(
                    **activity.dict(exclude={"auto_assign"}),
                    auto_assign=False,
                )
            ],
        )

        # Create a manual assignment
        await ActivityAssignmentService(session).create_many(
            applet_one_lucy_respondent.id,
            [
                ActivityAssignmentCreate(
                    activity_id=activity.id,
                    respondent_subject_id=lucy_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                ),
            ],
        )

        client.login(tom)

        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=lucy_applet_one_subject.id, activity_or_flow_id=str(activity.id)
        )
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.OK

        result = response.json()["result"]

        assert len(result) == 1

        subject_result = result[0]

        assert subject_result["id"] == str(tom_applet_one_subject.id)
        assert subject_result["submissionCount"] == 0
        assert subject_result["currentlyAssigned"] is True

    async def test_get_target_subjects_by_respondent_excludes_deleted_assignment(
        self,
        client,
        tom: User,
        tom_applet_one_subject: Subject,
        lucy_applet_one_subject: Subject,
        applet_one_lucy_respondent: AppletFull,
        session,
    ):
        activity = applet_one_lucy_respondent.activities[0]

        # Turn off auto-assignment
        activity_service = ActivityService(session, tom.id)
        await activity_service.remove_applet_activities(applet_one_lucy_respondent.id)
        await activity_service.update_create(
            applet_one_lucy_respondent.id,
            [
                ActivityUpdate(
                    **activity.dict(exclude={"auto_assign"}),
                    auto_assign=False,
                )
            ],
        )

        # Create a deleted assignment
        assignment_service = ActivityAssignmentService(session)
        await assignment_service.create_many(
            applet_one_lucy_respondent.id,
            [
                ActivityAssignmentCreate(
                    activity_id=activity.id,
                    respondent_subject_id=lucy_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                ),
            ],
        )
        await assignment_service.unassign_many(
            [
                ActivityAssignmentDelete(
                    activity_id=activity.id,
                    respondent_subject_id=lucy_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                )
            ]
        )

        client.login(tom)

        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=lucy_applet_one_subject.id, activity_or_flow_id=str(activity.id)
        )
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.OK

        assert response.json()["result"] == []

    async def test_get_target_subjects_by_respondent_multiple_assignments(
        self,
        client,
        tom: User,
        tom_applet_one_subject: Subject,
        lucy_applet_one_subject: Subject,
        pit_applet_one_subject: Subject,
        applet_one_shell_account: Subject,
        applet_one_lucy_respondent: AppletFull,
        applet_one_pit_respondent: AppletFull,
        session,
    ):
        activity = applet_one_lucy_respondent.activities[0]

        # Turn off auto-assignment
        activity_service = ActivityService(session, tom.id)
        await activity_service.remove_applet_activities(applet_one_lucy_respondent.id)
        await activity_service.update_create(
            applet_one_lucy_respondent.id,
            [
                ActivityUpdate(
                    **activity.dict(exclude={"auto_assign"}),
                    auto_assign=False,
                )
            ],
        )

        # Create a manual assignment
        await ActivityAssignmentService(session).create_many(
            applet_one_lucy_respondent.id,
            [
                ActivityAssignmentCreate(
                    activity_id=activity.id,
                    respondent_subject_id=lucy_applet_one_subject.id,
                    target_subject_id=tom_applet_one_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=activity.id,
                    respondent_subject_id=lucy_applet_one_subject.id,
                    target_subject_id=applet_one_shell_account.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=activity.id,
                    respondent_subject_id=tom_applet_one_subject.id,
                    target_subject_id=pit_applet_one_subject.id,
                ),
            ],
        )

        client.login(tom)

        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=lucy_applet_one_subject.id, activity_or_flow_id=str(activity.id)
        )
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.OK

        result = response.json()["result"]

        assert len(result) == 2

        tom_result = result[0]

        assert tom_result["id"] == str(tom_applet_one_subject.id)
        assert tom_result["submissionCount"] == 0
        assert tom_result["currentlyAssigned"] is True

        shell_account_result = result[1]

        assert shell_account_result["id"] == str(applet_one_shell_account.id)
        assert shell_account_result["submissionCount"] == 0
        assert shell_account_result["currentlyAssigned"] is True

    @pytest.mark.parametrize("subject_type", ["target", "respondent"])
    async def test_get_target_subjects_by_respondent_via_submission(
        self,
        client,
        tom: User,
        tom_applet_one_subject: Subject,
        lucy_applet_one_subject: Subject,
        applet_one_shell_account: Subject,
        subject_type: str,
        applet_one_lucy_respondent: AppletFull,
        answer_create_payload: dict,
        session: AsyncSession,
    ):
        activity = applet_one_lucy_respondent.activities[0]
        source_subject = lucy_applet_one_subject if subject_type == "respondent" else applet_one_shell_account

        # Turn off auto-assignment
        activity_service = ActivityService(session, tom.id)
        await activity_service.remove_applet_activities(applet_one_lucy_respondent.id)
        await activity_service.update_create(
            applet_one_lucy_respondent.id,
            [
                ActivityUpdate(
                    **activity.dict(exclude={"auto_assign"}),
                    auto_assign=False,
                )
            ],
        )

        # Create an answer
        await AnswerService(session, tom.id).create_answer(
            AppletAnswerCreate(
                **answer_create_payload,
                input_subject_id=lucy_applet_one_subject.id,
                source_subject_id=source_subject.id,
                target_subject_id=tom_applet_one_subject.id,
            )
        )

        client.login(tom)

        url = self.subject_target_by_respondent_url.format(
            respondent_subject_id=source_subject.id, activity_or_flow_id=str(activity.id)
        )
        response = await client.get(url)
        assert response.status_code == http.HTTPStatus.OK

        result = response.json()["result"]

        assert len(result) == 1

        tom_result = result[0]

        assert tom_result["id"] == str(tom_applet_one_subject.id)
        assert tom_result["submissionCount"] == 1
        assert tom_result["currentlyAssigned"] is False
