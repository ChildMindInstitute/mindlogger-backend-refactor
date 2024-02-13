import http
import json
import uuid
from copy import copy

import pytest
from asyncpg import UniqueViolationError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.crud.answers import AnswersCRUD
from apps.shared.test import BaseTest
from apps.subjects.crud import SubjectsCrud
from apps.subjects.domain import Subject, SubjectCreateRequest, SubjectRelationCreate
from apps.subjects.services import SubjectsService


@pytest.fixture
def create_shell_body():
    return SubjectCreateRequest(
        applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
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
def answer_create_payload():
    return dict(
        submit_id="270d86e0-2158-4d18-befd-86b3ce0122ae",
        applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
        activity_id="09e3dbf0-aefb-4d0e-9177-bdb321bf3611",
        version="1.0.0",
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
            scheduledEventId="eventId",
            localEndDate="2022-10-01",
            localEndTime="12:35:00",
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


class TestSubjects(BaseTest):
    fixtures = [
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "applets/fixtures/applet_histories.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_items.json",
        "activity_flows/fixtures/activity_flows.json",
        "activity_flows/fixtures/activity_flow_items.json",
        "activities/fixtures/activity_histories.json",
        "activities/fixtures/activity_item_histories.json",
        "activity_flows/fixtures/activity_flow_histories.json",
        "activity_flows/fixtures/activity_flow_item_histories.json",
        "workspaces/fixtures/workspaces.json",
        "subjects/fixtures/subjects.json",
    ]

    login_url = "/auth/login"
    subject_list_url = "/subjects"
    subject_detail_url = "/subjects/{subject_id}"
    subject_relation_url = (
        "/subjects/{subject_id}/relations/{source_subject_id}"
    )
    answer_url = "/answers"

    async def test_create_subject(self, client, create_shell_body):
        creator_id = "7484f34a-3acc-4ee6-8a94-fd7299502fa1"
        applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.subject_list_url, data=create_shell_body
        )
        assert response.status_code == 201
        payload = response.json()
        assert payload
        assert payload["result"]["appletId"] == applet_id
        assert payload["result"]["email"] is None
        assert payload["result"]["creatorId"] == creator_id
        assert payload["result"]["userId"] is None
        assert payload["result"]["language"] == "en"

    async def test_create_relation(self, client, create_shell_body):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.subject_list_url, data=create_shell_body
        )
        subject = response.json()

        source_subject_id = "ee5e2f55-8e32-40af-8ef9-24e332c31d7c"
        target_subject_id = subject["result"]["id"]

        body = SubjectRelationCreate(
            relation="father",
        )
        url = self.subject_relation_url.format(
            subject_id=target_subject_id, source_subject_id=source_subject_id
        )
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
        create_shell_body,
        subject_id,
        source_subject_id,
        exp_code,
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.subject_list_url, data=create_shell_body
        )
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
        url = self.subject_relation_url.format(
            subject_id=_target_subject_id, source_subject_id=_source_subject_id
        )
        await client.post(url, body.dict())

        url_delete = self.subject_relation_url.format(
            subject_id=subject_id if subject_id else _target_subject_id,
            source_subject_id=source_subject_id
            if source_subject_id
            else _source_subject_id,
        )
        res = await client.delete(url_delete)
        assert res.status_code == exp_code

    @pytest.mark.parametrize(
        "body,exp_status",
        (
            (
                # Duplicated secret id
                dict(secretUserId="f0dd4996-e0eb-461f-b2f8-ba873a674788"),
                http.HTTPStatus.BAD_REQUEST,
            ),
            (dict(secretUserId=str(uuid.uuid4())), http.HTTPStatus.OK),
            (
                dict(secretUserId=str(uuid.uuid4()), nickname="bob"),
                http.HTTPStatus.OK,
            ),
            (dict(nickname="bob"), http.HTTPStatus.UNPROCESSABLE_ENTITY),
        ),
    )
    async def test_update_subject(
        self, client, session, create_shell_body, body, exp_status
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.subject_list_url, data=create_shell_body
        )
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

    async def test_upsert_for_soft_deleted(
        self, session: AsyncSession, subject_schema, subject_updated_schema
    ):
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
        self, session, client, answer_create_payload, mock_kiq_report
    ):
        subject_id = uuid.UUID("ee5e2f55-8e32-40af-8ef9-24e332c31d7c")
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.answer_url, data=answer_create_payload
        )

        assert response.status_code == http.HTTPStatus.CREATED
        delete_url = self.subject_detail_url.format(subject_id=subject_id)
        res = await client.delete(delete_url, data=dict(deleteAnswers=False))
        assert res.status_code == http.HTTPStatus.OK

        subject = await SubjectsCrud(session).get_by_id(subject_id)
        assert subject, subject.is_deleted
        count = await AnswersCRUD(session).count(target_subject_id=subject_id)
        assert count

    async def test_successfully_delete_subject_with_answers(
        self, session, client, answer_create_payload, mock_kiq_report
    ):
        subject_id = uuid.UUID("ee5e2f55-8e32-40af-8ef9-24e332c31d7c")
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.answer_url, data=answer_create_payload
        )

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
            # Editor
            ("pitbronson@mail.com", "Test1234", http.HTTPStatus.FORBIDDEN),
            # Reviewer
            ("billbronson@mail.com", "Test1234!", http.HTTPStatus.FORBIDDEN),
        ),
    )
    async def test_error_try_delete_subject_by_not_owner(
        self,
        session,
        client,
        answer_create_payload,
        mock_kiq_report,
        email,
        password,
        expected,
    ):
        subject_id = uuid.UUID("ee5e2f55-8e32-40af-8ef9-24e332c31d7c")
        await client.login(self.login_url, email, password)
        delete_url = self.subject_detail_url.format(subject_id=subject_id)
        res = await client.delete(delete_url, data=dict(deleteAnswers=True))
        assert res.status_code == expected

    @pytest.mark.parametrize(
        "subject_id,expected_code",
        (
            ("89ba6774-4f48-4ff1-9d34-0e6efd24f03f", http.HTTPStatus.OK),
            (
                "ee96b767-4609-4b8b-93c5-e7b15b81c6f7",
                http.HTTPStatus.FORBIDDEN,
            ),
            (uuid.uuid4(), http.HTTPStatus.NOT_FOUND),
        ),
    )
    async def test_get_subject(self, client, subject_id, expected_code):
        await client.login(self.login_url, "reviewer@mail.com", "Test1234!")
        response = await client.get(
            self.subject_detail_url.format(subject_id=subject_id)
        )
        assert response.status_code == expected_code
        data = response.json()
        assert data
