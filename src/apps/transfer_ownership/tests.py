import http
import re
import uuid

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.domain import Role
from apps.applets.domain.applet_create_update import AppletReportConfiguration
from apps.applets.domain.applet_full import AppletFull
from apps.applets.service import AppletService
from apps.invitations.errors import ManagerInvitationExist
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.transfer_ownership.crud import TransferCRUD
from apps.transfer_ownership.errors import TransferEmailError
from apps.users.domain import User


@pytest.fixture
def applet_report_configuration_data(user: User) -> AppletReportConfiguration:
    return AppletReportConfiguration(
        report_server_ip="localhost",
        report_public_key="key",
        report_recipients=[user.email_encrypted],
        report_email_body="body",
        report_include_case_id=True,
        report_include_user_id=True,
    )


@pytest.fixture
async def applet_one_with_report_conf(
    applet_one: AppletFull,
    session: AsyncSession,
    tom: User,
    applet_report_configuration_data: AppletReportConfiguration,
) -> AppletFull:
    srv = AppletService(session, tom.id)
    await srv.set_report_configuration(applet_one.id, applet_report_configuration_data)
    applet = await srv.get_full_applet(applet_one.id)
    return applet


class TestTransfer(BaseTest):
    fixtures = [
        "transfer_ownership/fixtures/transfers.json",
        "invitations/fixtures/invitations.json",
    ]

    login_url = "/auth/login"
    transfer_url = "/applets/{applet_id}/transferOwnership"
    response_url = "/applets/{applet_id}/transferOwnership/{key}"
    applet_details_url = "/applets/{applet_id}"
    invite_manager_url = "/invitations/{applet_id}/managers"
    invite_accept_url = "/invitations/{key}/accept"
    workspace_applet_managers_list = "/workspaces/{owner_id}/applets/{applet_id}/managers"
    applet_encryption_url = f"{applet_details_url}/encryption"

    async def test_initiate_transfer(self, client: TestClient, applet_one: AppletFull):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = {"email": "lucy@gmail.com"}

        response = await client.post(
            self.transfer_url.format(applet_id=applet_one.id),
            data=data,
        )

        assert response.status_code == http.HTTPStatus.OK
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [data["email"]]
        assert TestMail.mails[0].subject == "Transfer ownership of an applet"

    async def test_initiate_transfer_fail(self, client: TestClient):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = {"email": "aloevdamirkhon@gmail.com"}

        response = await client.post(
            self.transfer_url.format(applet_id="00000000-0000-0000-0000-000000000012"),
            data=data,
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_decline_transfer(self, client: TestClient, mocker: MockerFixture, applet_one: AppletFull):
        resp = await client.login(self.login_url, "lucy@gmail.com", "Test123")
        lucy_id = resp.json()["result"]["user"]["id"]
        mock = mocker.patch("apps.transfer_ownership.crud.TransferCRUD.decline_by_key")
        key = "6a3ab8e6-f2fa-49ae-b2db-197136677da7"
        response = await client.delete(
            self.response_url.format(
                applet_id=applet_one.id,
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT
        mock.assert_awaited_once_with(uuid.UUID(key), uuid.UUID(lucy_id))

    async def test_decline_wrong_transfer(self, client: TestClient):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.delete(
            self.response_url.format(
                applet_id="00000000-0000-0000-0000-000000000000",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_re_decline_transfer(self, client: TestClient, applet_one: AppletFull):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.delete(
            self.response_url.format(
                applet_id=applet_one.id,
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT

        response = await client.delete(
            self.response_url.format(
                applet_id=applet_one.id,
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_accept_transfer(self, client: TestClient, mocker: MockerFixture, applet_one: AppletFull):
        resp = await client.login(self.login_url, "lucy@gmail.com", "Test123")
        lucy_id = resp.json()["result"]["user"]["id"]
        mock = mocker.patch("apps.transfer_ownership.crud.TransferCRUD.approve_by_key")
        key = "6a3ab8e6-f2fa-49ae-b2db-197136677da7"
        response = await client.post(
            self.response_url.format(
                applet_id=applet_one.id,
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        mock.assert_awaited_once_with(uuid.UUID(key), uuid.UUID(lucy_id))

    async def test_accept_wrong_transfer(self, client: TestClient):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.post(
            self.response_url.format(
                applet_id="00000000-0000-0000-0000-000000000000",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_re_accept_transfer(self, client: TestClient, applet_one: AppletFull):
        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.post(
            self.response_url.format(
                applet_id=applet_one.id,
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.OK

        response = await client.post(
            self.response_url.format(
                applet_id=applet_one.id,
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_accept_transfer_report_settings_are_kept(
        self, client: TestClient, applet_one_with_report_conf: AppletFull
    ):
        report_settings_keys = (
            "reportServerIp",
            "reportPublicKey",
            "reportRecipients",
            "reportEmailBody",
            "reportIncludeUserId",
            "reportIncludeCaseId",
        )
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        resp = await client.get(self.applet_details_url.format(applet_id=applet_one_with_report_conf.id))
        assert resp.status_code == http.HTTPStatus.OK
        resp_data = resp.json()["result"]
        # Fot this test all report settings are set for applet
        for key in report_settings_keys:
            assert resp_data[key]

        await client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await client.post(
            self.response_url.format(
                applet_id=applet_one_with_report_conf.id,
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )
        assert response.status_code == http.HTTPStatus.OK

        resp = await client.get(self.applet_details_url.format(applet_id=applet_one_with_report_conf.id))
        assert resp.status_code == http.HTTPStatus.OK
        resp_data = resp.json()["result"]
        # After accept transfership all report settings must be kept
        for key in report_settings_keys:
            assert resp_data[key]

    @pytest.mark.usefixtures("user")
    async def test_reinvite_manager_after_transfer(
        self, client: TestClient, user: User, mike: User, applet_one: AppletFull
    ):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        request_data = dict(
            email=user.email_encrypted,
            first_name=user.first_name,
            last_name=user.last_name,
            role=Role.MANAGER,
            language="en",
        )
        # send manager invite
        response = await client.post(
            self.invite_manager_url.format(applet_id=applet_one.id),
            data=request_data,
        )
        assert response.status_code == http.HTTPStatus.OK
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]

        # accept manager invite
        await client.login(self.login_url, user.email_encrypted, "Test1234!")
        key = response.json()["result"]["key"]
        response = await client.post(self.invite_accept_url.format(key=key))
        assert response.status_code == http.HTTPStatus.OK

        # transfer ownership to mike@gmail.com
        # initiate transfer
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = {"email": mike.email_encrypted}

        response = await client.post(
            self.transfer_url.format(applet_id=applet_one.id),
            data=data,
        )

        assert response.status_code == http.HTTPStatus.OK

        assert len(TestMail.mails) == 2
        assert TestMail.mails[0].recipients == [data["email"]]
        assert TestMail.mails[0].subject == "Transfer ownership of an applet"
        body = TestMail.mails[0].body
        regex = (
            r"\bkey=[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}&action=accept"  # noqa: E501
        )
        key = re.findall(regex, body)
        key = key[0][4:-14]

        # accept transfer
        await client.login(self.login_url, mike.email_encrypted, "Test1234")
        response = await client.post(
            self.response_url.format(
                applet_id=applet_one.id,
                key=key,
            ),
        )
        assert response.status_code == http.HTTPStatus.OK

        # check managers list
        response = await client.get(
            self.workspace_applet_managers_list.format(
                owner_id=mike.id,
                applet_id=applet_one.id,
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        email_role_map = dict()
        for res in result:
            email_role_map[res["email"]] = res["roles"]
        emails = list(email_role_map.keys())

        assert mike.email_encrypted in emails
        assert Role.OWNER in email_role_map["mike@gmail.com"]

        assert "user@example.com" in emails
        assert Role.MANAGER in email_role_map["user@example.com"]

        # try sending manager invite,
        request_data = dict(
            email="user@example.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.MANAGER,
            language="en",
        )
        response = await client.post(
            self.invite_manager_url.format(applet_id=applet_one.id),
            data=request_data,
        )
        assert response.status_code == ManagerInvitationExist.status_code
        assert response.json()["result"][0]["message"] == ManagerInvitationExist.message

    # TODO: move these tests to the unit tests for service and crud
    async def test_init_transfer__user_to_does_not_exist(
        self, client: TestClient, session: AsyncSession, applet_one: AppletFull
    ):
        resp = await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        from_user_id = resp.json()["result"]["user"]["id"]
        data = {"email": "userdoesnotexist@example.com"}
        applet_id = applet_one.id
        response = await client.post(
            self.transfer_url.format(applet_id=applet_id),
            data=data,
        )
        assert response.status_code == http.HTTPStatus.OK
        body = TestMail.mails[0].body
        regex = (
            r"\bkey=[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}&action=accept"  # noqa: E501
        )
        key = str(re.findall(regex, body)[0][4:-14])
        crud = TransferCRUD(session)
        transfer = await crud.get_by_key(uuid.UUID(key))
        assert transfer.to_user_id is None
        assert transfer.from_user_id == uuid.UUID(from_user_id)

    # TODO: move these tests to the unit tests for service and crud
    async def test_init_transfer__user_to_exists(
        self, client: TestClient, session: AsyncSession, lucy: User, applet_one: AppletFull
    ):
        resp = await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        from_user_id = resp.json()["result"]["user"]["id"]
        data = {"email": "lucy@gmail.com"}
        applet_id = applet_one.id
        response = await client.post(
            self.transfer_url.format(applet_id=applet_id),
            data=data,
        )
        assert response.status_code == http.HTTPStatus.OK
        body = TestMail.mails[0].body
        regex = (
            r"\bkey=[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}&action=accept"  # noqa: E501
        )
        key = str(re.findall(regex, body)[0][4:-14])
        crud = TransferCRUD(session)
        transfer = await crud.get_by_key(uuid.UUID(key))
        assert transfer.to_user_id == lucy.id
        assert transfer.from_user_id == uuid.UUID(from_user_id)

    async def test_init_transfer_owner_invite_themself(self, client: TestClient, applet_one: AppletFull):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        data = {"email": "tom@mindlogger.com"}
        applet_id = applet_one.id
        resp = await client.post(
            self.transfer_url.format(applet_id=applet_id),
            data=data,
        )
        assert resp.status_code == http.HTTPStatus.BAD_REQUEST
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == TransferEmailError.message
