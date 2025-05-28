import re
import uuid

import httpx
import pytest
from pytest_httpx import HTTPXMock
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.domain.applet_full import AppletFull
from apps.integrations.oneup_health.service.oneup_health import get_unique_short_id
from apps.shared.test.client import TestClient
from apps.subjects.domain import SubjectFull
from apps.subjects.services import SubjectsService
from apps.users import User


class TestOneupHealth:
    get_token_url = "integrations/oneup_health/subject/{subject_id}/token"
    get_token_by_submit_id_url = (
        "integrations/oneup_health/applet/{applet_id}/submission/{submit_id}/activity/{activity_id}/token"
    )

    @pytest.mark.asyncio
    async def test_get_token_creating_user_success(
        self,
        client: TestClient,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        httpx_mock: HTTPXMock,
    ):
        assert tom_applet_one_subject.id
        app_user_id = get_unique_short_id(submit_id=tom_applet_one_subject.id, activity_id=None)

        # mock create user
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="POST",
            json={
                "success": True,
                "code": "code_test",
                "oneup_user_id": 1,
                "app_user_id": app_user_id,
            },
        )

        # mock get token
        httpx_mock.add_response(
            url=re.compile(".*/oauth2/token.*"),
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
        assert result["oneupUserId"] == 1
        assert result["appUserId"] == app_user_id

    @pytest.mark.asyncio
    async def test_get_token_by_submit_id_creating_user_success(
        self,
        client: TestClient,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        httpx_mock: HTTPXMock,
        applet_one: AppletFull,
    ):
        submit_id = uuid.uuid4()
        activity_id = applet_one.activities[0].id

        app_user_id = get_unique_short_id(submit_id=submit_id, activity_id=activity_id)
        # mock create user
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="POST",
            json={"success": True, "code": "code_test", "oneup_user_id": 1, "app_user_id": app_user_id},
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
        response = await client.get(
            url=self.get_token_by_submit_id_url.format(
                applet_id=tom_applet_one_subject.applet_id, submit_id=submit_id, activity_id=activity_id
            )
        )
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["accessToken"] == "token_test"
        assert result["refreshToken"] == "refresh_token_test"
        assert result["oneupUserId"] == 1
        assert result["appUserId"] == app_user_id

    @pytest.mark.asyncio
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
            status_code=400,
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

        assert tom_applet_one_subject.id is not None
        app_user_id = get_unique_short_id(submit_id=tom_applet_one_subject.id, activity_id=None)
        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["accessToken"] == "token_test"
        assert result["refreshToken"] == "refresh_token_test"
        assert result["oneupUserId"] == 1
        assert result["appUserId"] == app_user_id

    @pytest.mark.asyncio
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

        app_user_id = get_unique_short_id(submit_id=tom_applet_one_subject.id, activity_id=None)
        # mock create auth code
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user/auth-code"),
            method="POST",
            json={
                "success": True,
                "code": "code_test",
                "oneup_user_id": 1,
                "active": True,
                "app_user_id": app_user_id,
            },
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 200
        result = response.json()["result"]
        assert result["accessToken"] == "token_test"
        assert result["refreshToken"] == "refresh_token_test"
        assert result["oneupUserId"] == 1
        assert result["appUserId"] == app_user_id

    async def test_get_token_error_creating_user(
        self, client: TestClient, tom: User, tom_applet_one_subject: SubjectFull, httpx_mock: HTTPXMock
    ):
        # mock create user
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="POST",
            json={"success": False, "error": "Any error message"},
            status_code=200,
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 502
        result = response.json()["result"]
        assert result[0]["message"] == "1UpHealth request failed."

    async def test_token_expired_error(
        self,
        client: TestClient,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        httpx_mock: HTTPXMock,
    ):
        # Mock token expired error
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="POST",
            json={"message": "Unauthorized"},
            status_code=401,
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 502
        result = response.json()["result"]
        assert result[0]["message"] == "1UpHealth access token has expired."

    async def test_get_token_error_outside_us(
        self, client: TestClient, tom: User, tom_applet_one_subject: SubjectFull, httpx_mock: HTTPXMock
    ):
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"), method="POST", json={"message": "Forbidden"}, status_code=403
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 502
        result = response.json()["result"]
        assert result[0]["message"] == "Access to 1UpHealth is currently restricted to users within the United States."

    async def test_service_unavailable_error(
        self,
        client: TestClient,
        tom: User,
        tom_applet_one_subject: SubjectFull,
        httpx_mock: HTTPXMock,
    ):
        # Mock service unavailable error
        httpx_mock.add_response(
            url=re.compile(".*/user-management/v1/user"),
            method="POST",
            json={"message": "Service Unavailable"},
            status_code=503,
        )

        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 502
        result = response.json()["result"]
        assert result[0]["message"] == "1UpHealth service is currently unavailable."

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
        assert response.status_code == 502
        result = response.json()["result"]
        assert result[0]["message"] == "1UpHealth request failed."

    async def test_get_token_error_timeout(
        self,
        client: TestClient,
        tom: User,
        session: AsyncSession,
        tom_applet_one_subject: SubjectFull,
        httpx_mock: HTTPXMock,
    ):
        # Mock HTTP error for audit events
        httpx_mock.add_exception(
            url=re.compile(".*/user-management/v1/user"),
            method="POST",
            exception=httpx.ConnectTimeout("Connection Timeout"),
        )
        client.login(tom)
        response = await client.get(url=self.get_token_url.format(subject_id=tom_applet_one_subject.id))
        assert response.status_code == 502
        result = response.json()["result"]
        assert result[0]["message"] == "1UpHealth request failed."

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
        assert response.status_code == 502
        result = response.json()["result"]
        assert result[0]["message"] == "1UpHealth service is currently unavailable."

    @pytest.mark.asyncio
    async def test_refresh_token_success(
        self,
        client: TestClient,
        tom: User,
        httpx_mock: HTTPXMock,
    ):
        # Mock refresh token response - no app_user_id in the response
        # as it will be generated by the service based on submit_id and activity_id
        httpx_mock.add_response(
            url=re.compile(".*/oauth2/token"),
            method="POST",
            json={
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
            },
        )

        client.login(tom)
        response = await client.post(
            "/integrations/oneup_health/refresh_token",
            {
                "refreshToken": "old_refresh_token",
            },
        )

        assert response.status_code == 200
        result = response.json()["result"]
        assert result["accessToken"] == "new_access_token"
        assert result["refreshToken"] == "new_refresh_token"

    @pytest.mark.asyncio
    async def test_refresh_token_without_ids(
        self,
        client: TestClient,
        tom: User,
        httpx_mock: HTTPXMock,
    ):
        # Mock refresh token response
        httpx_mock.add_response(
            url=re.compile(".*/oauth2/token"),
            method="POST",
            json={
                "access_token": "new_access_token",
                "refresh_token": "new_refresh_token",
            },
        )

        client.login(tom)
        response = await client.post(
            "/integrations/oneup_health/refresh_token",
            {
                "refreshToken": "old_refresh_token",
            },
        )

        assert response.status_code == 200
        result = response.json()["result"]
        assert result["accessToken"] == "new_access_token"
        assert result["refreshToken"] == "new_refresh_token"
