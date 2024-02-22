import http
import json
import uuid
from copy import copy

import pytest
from asyncpg import UniqueViolationError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.crud.answers import AnswersCRUD
from apps.applets.domain.applet_full import AppletFull
from apps.shared.test import BaseTest
from apps.subjects.crud import SubjectsCrud
from apps.subjects.domain import Subject, SubjectCreateRequest, SubjectRelationCreate
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
    ).dict()


@pytest.fixture
def subject_schema():
    return Subject(
        applet_id=uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b1"),
        email="subject@mail.com",
        creator_id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa1"),
        user_id=uuid.UUID("6a180cd9-db2b-4195-a5ac-30a8733dfb06"),
        language="en",
        first_name="first_name",
        last_name="last_name",
        secret_user_id="secret_user_id",
        nickname="nickname",
    )


@pytest.fixture
def subject_updated_schema(subject_schema):
    return Subject(
        applet_id=subject_schema.applet_id,
        email=f"new-{subject_schema.email}",
        creator_id=subject_schema.user_id,
        user_id=subject_schema.user_id,
        language="en",
        first_name=f"new-{subject_schema.first_name}",
        last_name=f"new-{subject_schema.last_name}",
        secret_user_id=f"new-{subject_schema.secret_user_id}",
        nickname=f"new-{subject_schema.nickname}",
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
            dict(secretUserId=str(uuid.uuid4()), nickname="bob"),
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
async def lucy_invitation_payload(lucy: User) -> dict:
    return dict(
        email=lucy.email_encrypted,
        first_name=lucy.first_name,
        last_name=lucy.last_name,
        language="en",
        role=Role.MANAGER,
    )


class TestSubjects(BaseTest):
    fixtures = [
        "workspaces/fixtures/workspaces.json",
    ]

    login_url = "/auth/login"
    subject_list_url = "/subjects"
    subject_detail_url = "/subjects/{subject_id}"
    subject_relation_url = "/subjects/{subject_id}/relations/{source_subject_id}"
    answer_url = "/answers"

    async def test_create_subject(self, client, tom: User, applet_one: AppletFull, create_shell_body):
        creator_id = str(tom.id)
        applet_id = str(applet_one.id)
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.post(self.subject_list_url, data=create_shell_body)
        assert response.status_code == 201
        payload = response.json()
        assert payload
        assert payload["result"]["appletId"] == applet_id
        assert payload["result"]["email"] is None
        assert payload["result"]["creatorId"] == creator_id
        assert payload["result"]["userId"] is None
        assert payload["result"]["language"] == "en"

    async def test_create_relation(self, client, tom: User, create_shell_body, tom_applet_one_subject):
        subject_id = tom_applet_one_subject.id
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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
        else:
            exp_secret_id = create_shell_body.get("secret_user_id")
            exp_nickname = create_shell_body.get("nickname")

        assert subject.secret_user_id == exp_secret_id
        assert subject.nickname == exp_nickname

    async def test_upsert_for_soft_deleted(self, session: AsyncSession, subject_schema, subject_updated_schema):
        service = SubjectsService(session, subject_schema.user_id)
        original_subject = await service.create(subject_schema)
        assert original_subject.id
        await service.delete(original_subject.id)
        result_subject = await service.create(subject_updated_schema)
        assert result_subject.id
        actual_subject = await service.get(result_subject.id)
        assert actual_subject
        for field_name in Subject.__fields__.keys():
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
        for field_name in Subject.__fields__.keys():
            actual = getattr(actual_subject, field_name)
            expected = getattr(original_subject, field_name)
            assert actual == expected

    async def test_successfully_delete_subject_without_answers(
        self, session, client, tom: User, tom_applet_one_subject, answer_create_payload, mock_kiq_report
    ):
        subject_id = tom_applet_one_subject.id
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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
        "email,password,expected",
        (
            # Owner
            ("tom@mindlogger.com", "Test1234!", http.HTTPStatus.OK),
            # Manager
            ("lucy@gmail.com", "Test123", http.HTTPStatus.OK),
            # Coordinator
            ("bob@gmail.com", "Test1234!", http.HTTPStatus.OK),
            # Editor, reviewer
            ("pitbronson@mail.com", "Test1234", http.HTTPStatus.FORBIDDEN),
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
        email,
        password,
        expected,
    ):
        subject_id = tom_applet_one_subject.id
        await client.login(self.login_url, email, password)
        delete_url = self.subject_detail_url.format(subject_id=subject_id)
        res = await client.delete(delete_url, data=dict(deleteAnswers=True))
        assert res.status_code == expected

    async def test_get_subject(self, client, tom: User, tom_applet_one_subject: Subject, lucy, lucy_create):
        subject_id = tom_applet_one_subject.id
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        response = await client.get(self.subject_detail_url.format(subject_id=subject_id))
        assert response.status_code == http.HTTPStatus.OK
        data = response.json()
        assert data
        res = data["result"]
        assert set(res.keys()) == {"secretUserId", "nickname", "lastSeen"}
        assert res["secretUserId"] == tom_applet_one_subject.secret_user_id
        assert res["nickname"] == tom_applet_one_subject.nickname

        # not found
        response = await client.get(self.subject_detail_url.format(subject_id=uuid.uuid4()))
        assert response.status_code == http.HTTPStatus.NOT_FOUND

        # forbidden
        await client.login(self.login_url, lucy.email_encrypted, lucy_create.password)
        response = await client.get(self.subject_detail_url.format(subject_id=subject_id))
        assert response.status_code == http.HTTPStatus.FORBIDDEN

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
        await client.login(self.login_url, pit.email_encrypted, pit_create.password)
        response = await client.get(self.subject_detail_url.format(subject_id=subject_id))
        assert response.status_code == http.HTTPStatus.FORBIDDEN

        # allowed for reviewer with subject assigned
        await client.login(self.login_url, lucy.email_encrypted, lucy_create.password)
        response = await client.get(self.subject_detail_url.format(subject_id=subject_id))
        assert response.status_code == http.HTTPStatus.OK
        data = response.json()
        assert data

    async def test_editor_remove_respondent_access_error(
        self, client, session, tom, mike, lucy, applet_one: AppletFull, applet_one_lucy_respondent
    ):
        roles_to_delete = [Role.OWNER, Role.COORDINATOR, Role.MANAGER, Role.SUPER_ADMIN, Role.REVIEWER]
        await UserAppletAccessCRUD(session).delete_user_roles(applet_one.id, mike.id, roles_to_delete)
        await client.login(self.login_url, mike.email_encrypted, "Test1234")
        subject = await SubjectsService(session, tom.id).get_by_user_and_applet(lucy.id, applet_one.id)
        assert subject
        delete_url = self.subject_detail_url.format(subject_id=subject.id)
        response = await client.delete(delete_url, data=dict(deleteAnswers=False))
        assert response.status_code == http.HTTPStatus.FORBIDDEN

    async def test_workspace_coordinator_remove_respondent_access(
        self, client, session, lucy, applet_one, user, applet_one_bob_coordinator, applet_one_lucy_respondent, bob, tom
    ):
        await client.login(self.login_url, bob.email_encrypted, "Test1234!")
        subject = await SubjectsService(session, tom.id).get_by_user_and_applet(lucy.id, applet_one.id)
        assert subject
        delete_url = self.subject_detail_url.format(subject_id=subject.id)
        response = await client.delete(delete_url, data=dict(deleteAnswers=False))
        assert response.status_code == http.HTTPStatus.OK
