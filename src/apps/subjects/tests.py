import http
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.test import BaseTest
from apps.subjects.crud import SubjectsCrud
from apps.subjects.domain import (
    Subject,
    SubjectCreateRequest,
    SubjectRespondentCreate,
)
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
        user_id=uuid.UUID("7484f34a-3acc-4ee6-8a94-fd7299502fa1"),
        language="en",
        first_name="first_name",
        last_name="last_name",
        secret_user_id="secret_user_id",
        nickname="nickname",
    )


class TestSubjects(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "subjects/fixtures/subjects.json",
    ]

    login_url = "/auth/login"
    subject_list_url = "/subjects"
    subject_detail_url = "/subjects/{subject_id}"
    subject_respondent_url = "/subjects/{subject_id}/respondents"
    subject_respondent_details_url = (
        "/subjects/{subject_id}/respondents/{respondent_id}"
    )

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

    async def test_add_respondent(self, client, create_shell_body):
        creator_id = "7484f34a-3acc-4ee6-8a94-fd7299502fa1"
        applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.subject_list_url, data=create_shell_body
        )
        subject = response.json()
        body = SubjectRespondentCreate(
            user_id=creator_id,
            subject_id=subject["result"]["id"],
            applet_id=applet_id,
            relation="father",
        )
        url = self.subject_respondent_url.format(
            subject_id=subject["result"]["id"]
        )
        res = await client.post(url, body)
        assert res.status_code == http.HTTPStatus.OK

    @pytest.mark.parametrize(
        "subject_id,respondent_id,exp_code",
        (
            (uuid.uuid4(), None, http.HTTPStatus.NOT_FOUND),
            (None, uuid.uuid4(), http.HTTPStatus.NOT_FOUND),
            (None, None, http.HTTPStatus.OK),
        ),
    )
    async def test_remove_respondent(
        self, client, create_shell_body, subject_id, respondent_id, exp_code
    ):
        creator_id = "7484f34a-3acc-4ee6-8a94-fd7299502fa1"
        applet_id = "92917a56-d586-4613-b7aa-991f2c4b15b1"
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.post(
            self.subject_list_url, data=create_shell_body
        )
        subject = response.json()
        body = SubjectRespondentCreate(
            user_id=creator_id,
            subject_id=subject["result"]["id"],
            applet_id=applet_id,
            relation="father",
        )
        url = self.subject_respondent_url.format(
            subject_id=subject["result"]["id"]
        )
        respondent_res = await client.post(url, body.dict())
        subject = respondent_res.json()
        subject_id_ = subject["result"]["id"]
        respondent_id_ = subject["result"]["subjects"][0]["userId"]
        url_delete = self.subject_respondent_details_url.format(
            subject_id=subject_id if subject_id else subject_id_,
            respondent_id=respondent_id if respondent_id else respondent_id_,
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
        subject = await SubjectsCrud(session).get_by_id(subject["id"])
        if exp_status == http.HTTPStatus.OK:
            exp_secret_id = body.get("secretUserId")
            exp_nickname = body.get("nickname")
        else:
            exp_secret_id = create_shell_body.get("secret_user_id")
            exp_nickname = create_shell_body.get("nickname")

        assert subject.secret_user_id == exp_secret_id
        assert subject.nickname == exp_nickname

    async def test_upsert_test(self, session: AsyncSession, subject_schema):
        service = SubjectsService(session, subject_schema.user_id)
        original_subject = await service.create(subject_schema)

        updated_subject = Subject(
            applet_id=uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b1"),
            email=f"new-{original_subject.email}",
            creator_id=original_subject.user_id,
            user_id=original_subject.user_id,
            language="en",
            first_name=f"new-{original_subject.first_name}",
            last_name=f"new-{original_subject.last_name}",
            secret_user_id=f"new-{original_subject.secret_user_id}",
            nickname=f"new-{original_subject.nickname}",
        )
        result_subject = await service.create(updated_subject)
        assert result_subject.id
        actual_subject = await service.get(result_subject.id)
        assert actual_subject
        assert actual_subject.applet_id == updated_subject.applet_id
        assert actual_subject.email == updated_subject.email
        assert actual_subject.creator_id == updated_subject.creator_id
        assert actual_subject.user_id == updated_subject.user_id
        assert actual_subject.language == updated_subject.language
        assert actual_subject.first_name == updated_subject.first_name
        assert actual_subject.last_name == updated_subject.last_name
        assert actual_subject.secret_user_id == updated_subject.secret_user_id
        assert actual_subject.nickname == updated_subject.nickname
