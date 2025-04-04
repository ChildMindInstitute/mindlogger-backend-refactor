import re

from pytest_httpx import HTTPXMock
from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.test.client import TestClient
from apps.subjects.domain import SubjectFull
from apps.subjects.services import SubjectsService
from apps.users import User


class TestOneupHealth:
    get_token_url = "integrations/oneup_health/subject/{subject_id}/token"

    async def test_get_token_creating_user_success(
        self,
        client: TestClient,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        httpx_mock: HTTPXMock,
    ):
        # mock create user
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="POST",
            json={
                "success": True,
                "code": "code_test",
                "oneup_user_id": 1,
            },
        )

        # mock get token
        httpx_mock.add_response(
            url=re.compile(".*/oauth2/token"),
            method="POST",
            json={
                "access_token": "token_test",
                "refresh_token": "refresh_token_test",
            },
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["accessToken"] == "token_test"
        assert result["refreshToken"] == "refresh_token_test"
        assert result["subjectId"] == str(tom_applet_one_subject.id)
        assert result["oneupUserId"] == 1

    async def test_get_token_user_already_exists_success(
        self,
        client: TestClient,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        httpx_mock: HTTPXMock,
    ):
        # mock create user (already exists)
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="POST",
            json={"success": False, "error": "this user already exists"},
        )

        # mock create auth code
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user/auth-code"),
            method="POST",
            json={
                "success": True,
                "code": "code_test",
                "oneup_user_id": 1,
                "active": True,
            },
        )

        # mock get token
        httpx_mock.add_response(
            url=re.compile(".*/oauth2/token"),
            method="POST",
            json={
                "access_token": "token_test",
                "refresh_token": "refresh_token_test",
            },
        )

        # mock ge user
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="GET",
            json={
                "entry": [{"oneup_user_id": 1}],
                "success": True,
            },
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["accessToken"] == "token_test"
        assert result["refreshToken"] == "refresh_token_test"
        assert result["subjectId"] == str(tom_applet_one_subject.id)
        assert result["oneupUserId"] == 1

    async def test_get_token_without_creating_user(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        tom_applet_one_subject: SubjectFull,
        httpx_mock: HTTPXMock,
    ):
        subject_service = SubjectsService(session, tom.id)
        assert tom_applet_one_subject.id
        await subject_service.update(tom_applet_one_subject.id, meta={"oneup_user_id": 1})

        # mock get token
        httpx_mock.add_response(
            url=re.compile(".*/oauth2/token"),
            method="POST",
            json={
                "access_token": "token_test",
                "refresh_token": "refresh_token_test",
            },
        )

        # mock create auth code
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user/auth-code"),
            method="POST",
            json={
                "success": True,
                "code": "code_test",
                "oneup_user_id": 1,
                "active": True,
            },
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["accessToken"] == "token_test"
        assert result["refreshToken"] == "refresh_token_test"
        assert result["subjectId"] == str(tom_applet_one_subject.id)
        assert result["oneupUserId"] == 1

    async def test_get_token_error_outside_us(
        self, client: TestClient, tom: User, tom_applet_one_subject: SubjectFull, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"), method="POST", json={"message": "Forbidden"}, status_code=403
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 500
        result = response.json()["result"]
        assert (
            result[0]["message"] == "Access to OneUp Health is currently restricted to users within the United States."
        )

    async def test_get_token_error_creating_user(
        self, client: TestClient, tom: User, tom_applet_one_subject: SubjectFull, httpx_mock: HTTPXMock
    ):
        # mock create user
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="POST",
            json={"success": False, "error": "Any error message"},
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 500
        result = response.json()["result"]
        assert result[0]["message"] == "OneUp Health request failed."

    async def test_get_token_error_getting_code(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        tom_applet_one_subject: SubjectFull,
        httpx_mock: HTTPXMock,
    ):
        subject_service = SubjectsService(session, tom.id)
        assert tom_applet_one_subject.id
        await subject_service.update(tom_applet_one_subject.id, meta={"oneup_user_id": 1})

        # mock create auth code
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user/auth-code"),
            method="POST",
            json={"success": False, "error": "this user does not exist"},
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 500
        result = response.json()["result"]
        assert result[0]["message"] == "OneUp Health request failed."

    async def test_get_token_error_getting_token(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        tom_applet_one_subject: SubjectFull,
        httpx_mock: HTTPXMock,
    ):
        subject_service = SubjectsService(session, tom.id)
        assert tom_applet_one_subject.id
        await subject_service.update(tom_applet_one_subject.id, meta={"oneup_user_id": 1})

        # mock create auth code
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user/auth-code"),
            method="POST",
            json={
                "success": True,
                "code": "code_test",
                "oneup_user_id": 1,
                "active": True,
            },
        )

        # mock get token
        httpx_mock.add_response(
            url=re.compile(".*/oauth2/token"),
            method="POST",
            json={"error": "server_error", "error_description": "Cannot read property 'code' of undefined"},
            status_code=503,
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 500
        result = response.json()["result"]
        assert (
            result[0]["message"]
            == '{"error":"server_error","error_description":"Cannot read property \'code\' of undefined"}'
        )
