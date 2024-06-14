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
from apps.authentication.errors import PermissionsError
from apps.invitations.constants import InvitationStatus
from apps.invitations.errors import ManagerInvitationExist
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.subjects.services import SubjectsService
from apps.transfer_ownership.crud import TransferCRUD
from apps.transfer_ownership.errors import TransferEmailError
from apps.users.domain import User
from apps.workspaces.service.user_applet_access import UserAppletAccessService


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


@pytest.fixture
async def applet_one_lucy_respondent(session: AsyncSession, applet_one: AppletFull, tom, lucy) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.RESPONDENT)
    return applet_one


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

    async def test_initiate_transfer(self, client: TestClient, applet_one: AppletFull, tom: User, mailbox: TestMail):
        client.login(tom)
        data = {"email": "lucy@gmail.com"}

        response = await client.post(
            self.transfer_url.format(applet_id=applet_one.id),
            data=data,
        )

        assert response.status_code == http.HTTPStatus.OK
        assert len(mailbox.mails) == 1
        assert mailbox.mails[0].recipients == [data["email"]]
        assert mailbox.mails[0].subject == "Transfer ownership of an applet"

    async def test_initiate_transfer_fail(self, client: TestClient, tom: User):
        client.login(tom)
        data = {"email": "aloevdamirkhon@gmail.com"}

        response = await client.post(
            self.transfer_url.format(applet_id="00000000-0000-0000-0000-000000000012"),
            data=data,
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_decline_transfer(
        self, client: TestClient, mocker: MockerFixture, applet_one: AppletFull, lucy: User
    ):
        client.login(lucy)
        mock = mocker.patch("apps.transfer_ownership.crud.TransferCRUD.decline_by_key")
        key = "6a3ab8e6-f2fa-49ae-b2db-197136677da7"
        response = await client.delete(
            self.response_url.format(
                applet_id=applet_one.id,
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.NO_CONTENT
        mock.assert_awaited_once_with(uuid.UUID(key), lucy.id)

    async def test_decline_wrong_transfer(self, client: TestClient, lucy: User):
        client.login(lucy)
        response = await client.delete(
            self.response_url.format(
                applet_id="00000000-0000-0000-0000-000000000000",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_re_decline_transfer(self, client: TestClient, applet_one: AppletFull, lucy: User):
        client.login(lucy)
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

    async def test_accept_transfer(
        self, client: TestClient, mocker: MockerFixture, applet_one: AppletFull, lucy: User, session: AsyncSession
    ):
        client.login(lucy)
        mock = mocker.patch("apps.transfer_ownership.crud.TransferCRUD.approve_by_key")
        key = "6a3ab8e6-f2fa-49ae-b2db-197136677da7"
        response = await client.post(
            self.response_url.format(
                applet_id=applet_one.id,
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        mock.assert_awaited_once_with(uuid.UUID(key), lucy.id)
        lucy_subject = await SubjectsService(session, lucy.id).get_by_user_and_applet(lucy.id, applet_one.id)
        assert lucy_subject
        assert lucy_subject.email == lucy.email_encrypted
        assert lucy_subject.nickname == f"{lucy.first_name} {lucy.last_name}"

    async def test_accept_transfer_if_subject_already_exists(
        self,
        client: TestClient,
        mocker: MockerFixture,
        applet_one: AppletFull,
        session: AsyncSession,
        applet_one_lucy_respondent: AppletFull,
        lucy: User,
    ):
        client.login(lucy)
        mock = mocker.patch("apps.transfer_ownership.crud.TransferCRUD.approve_by_key")
        key = "6a3ab8e6-f2fa-49ae-b2db-197136677da7"
        response = await client.post(
            self.response_url.format(
                applet_id=applet_one.id,
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        mock.assert_awaited_once_with(uuid.UUID(key), lucy.id)
        lucy_subject = await SubjectsService(session, lucy.id).get_by_user_and_applet(lucy.id, applet_one.id)
        assert lucy_subject
        assert lucy_subject.email == lucy.email_encrypted
        assert lucy_subject.nickname == f"{lucy.first_name} {lucy.last_name}"

    async def test_accept_transfer_if_deleted_subject_already_exists(
        self,
        client: TestClient,
        mocker: MockerFixture,
        applet_one: AppletFull,
        session: AsyncSession,
        applet_one_lucy_respondent: AppletFull,
        lucy: User,
    ):
        client.login(lucy)
        mock = mocker.patch("apps.transfer_ownership.crud.TransferCRUD.approve_by_key")
        key = "6a3ab8e6-f2fa-49ae-b2db-197136677da7"

        subject_service = SubjectsService(session, lucy.id)
        lucy_subject = await subject_service.get_by_user_and_applet(lucy.id, applet_one.id)
        assert lucy_subject
        assert lucy_subject.id
        await subject_service.delete(lucy_subject.id)
        response = await client.post(
            self.response_url.format(
                applet_id=applet_one.id,
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.OK
        mock.assert_awaited_once_with(uuid.UUID(key), lucy.id)
        lucy_subject = await subject_service.get_by_user_and_applet(lucy.id, applet_one.id)
        assert lucy_subject
        assert not lucy_subject.is_deleted
        assert lucy_subject.email == lucy.email_encrypted
        assert lucy_subject.nickname == f"{lucy.first_name} {lucy.last_name}"

    async def test_accept_wrong_transfer(self, client: TestClient, lucy: User):
        client.login(lucy)
        response = await client.post(
            self.response_url.format(
                applet_id="00000000-0000-0000-0000-000000000000",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND

    async def test_re_accept_transfer(self, client: TestClient, applet_one: AppletFull, lucy: User):
        client.login(lucy)
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
        self, client: TestClient, applet_one_with_report_conf: AppletFull, tom: User, lucy
    ):
        report_settings_keys = (
            "reportServerIp",
            "reportPublicKey",
            "reportRecipients",
            "reportEmailBody",
            "reportIncludeUserId",
            "reportIncludeCaseId",
        )
        client.login(tom)
        resp = await client.get(self.applet_details_url.format(applet_id=applet_one_with_report_conf.id))
        assert resp.status_code == http.HTTPStatus.OK
        resp_data = resp.json()["result"]
        # Fot this test all report settings are set for applet
        for key in report_settings_keys:
            assert resp_data[key]

        client.login(lucy)
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
        self, client: TestClient, user: User, mike: User, applet_one: AppletFull, tom: User, mailbox: TestMail
    ):
        client.login(tom)
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
        assert len(mailbox.mails) == 1
        assert mailbox.mails[0].recipients == [request_data["email"]]

        # accept manager invite
        client.login(user)
        key = response.json()["result"]["key"]
        response = await client.post(self.invite_accept_url.format(key=key))
        assert response.status_code == http.HTTPStatus.OK

        # transfer ownership to mike@gmail.com
        # initiate transfer
        client.login(tom)
        data = {"email": mike.email_encrypted}

        response = await client.post(
            self.transfer_url.format(applet_id=applet_one.id),
            data=data,
        )

        assert response.status_code == http.HTTPStatus.OK

        assert len(mailbox.mails) == 2
        assert mailbox.mails[0].recipients == [data["email"]]
        assert mailbox.mails[0].subject == "Transfer ownership of an applet"
        body = mailbox.mails[0].body
        regex = (
            r"\bkey=[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}&action=accept"
        )
        key = re.findall(regex, body)
        key = key[0][4:-14]

        # accept transfer
        client.login(mike)
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
            if res["status"] == InvitationStatus.APPROVED:
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

    async def test_init_transfer__user_to_does_not_exist(
        self, client: TestClient, session: AsyncSession, applet_one: AppletFull, tom: User, mocker: MockerFixture
    ):
        client.login(tom)
        data = {"email": "userdoesnotexist@example.com"}
        applet_id = applet_one.id
        key = uuid.uuid4()
        mocker.patch("uuid.uuid4", return_value=key)
        response = await client.post(
            self.transfer_url.format(applet_id=applet_id),
            data=data,
        )
        assert response.status_code == http.HTTPStatus.OK
        crud = TransferCRUD(session)
        transfer = await crud.get_by_key(key)
        assert transfer.to_user_id is None
        assert transfer.from_user_id == tom.id

    async def test_init_transfer__user_to_exists(
        self,
        client: TestClient,
        session: AsyncSession,
        lucy: User,
        applet_one: AppletFull,
        tom: User,
        mocker: MockerFixture,
    ):
        client.login(tom)
        data = {"email": lucy.email_encrypted}
        applet_id = applet_one.id
        key = uuid.uuid4()
        mocker.patch("uuid.uuid4", return_value=key)
        response = await client.post(
            self.transfer_url.format(applet_id=applet_id),
            data=data,
        )
        assert response.status_code == http.HTTPStatus.OK
        crud = TransferCRUD(session)
        transfer = await crud.get_by_key(key)
        assert transfer.to_user_id == lucy.id
        assert transfer.from_user_id == tom.id

    async def test_init_transfer_owner_invite_themself(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)
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

    async def test_accept_transfer__user_not_in_transfer(
        self, client: TestClient, applet_one: AppletFull, tom: User, lucy: User, user: User, mocker: MockerFixture
    ):
        client.login(tom)
        data = {"email": lucy.email_encrypted}
        key = uuid.uuid4()
        mocker.patch("uuid.uuid4", return_value=key)
        resp = await client.post(self.transfer_url.format(applet_id=applet_one.id), data=data)
        assert resp.status_code == http.HTTPStatus.OK

        # Transfer sent for lucy
        client.login(user)
        resp = await client.post(self.response_url.format(applet_id=applet_one.id, key=key))
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == PermissionsError.message

    async def test_accept_transfer__applet_not_in_transfer(
        self,
        client: TestClient,
        applet_one: AppletFull,
        applet_two: AppletFull,
        tom: User,
        lucy: User,
        mocker: MockerFixture,
    ):
        client.login(tom)
        data = {"email": lucy.email_encrypted}
        key = uuid.uuid4()
        mocker.patch("uuid.uuid4", return_value=key)
        resp = await client.post(self.transfer_url.format(applet_id=applet_one.id), data=data)
        assert resp.status_code == http.HTTPStatus.OK

        client.login(lucy)
        # Transfer sent for applet_one
        resp = await client.post(self.response_url.format(applet_id=applet_two.id, key=key))
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == PermissionsError.message

    async def test_decline_transfer__user_not_in_transfer(
        self, client: TestClient, applet_one: AppletFull, tom: User, lucy: User, user: User, mocker: MockerFixture
    ):
        client.login(tom)
        data = {"email": lucy.email_encrypted}
        key = uuid.uuid4()
        mocker.patch("uuid.uuid4", return_value=key)
        resp = await client.post(self.transfer_url.format(applet_id=applet_one.id), data=data)
        assert resp.status_code == http.HTTPStatus.OK

        # Transfer sent for lucy
        client.login(user)
        resp = await client.delete(self.response_url.format(applet_id=applet_one.id, key=key))
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == PermissionsError.message

    async def test_decline_transfer__applet_not_in_transfer(
        self,
        client: TestClient,
        applet_one: AppletFull,
        applet_two: AppletFull,
        tom: User,
        lucy: User,
        mocker: MockerFixture,
    ):
        client.login(tom)
        data = {"email": lucy.email_encrypted}
        key = uuid.uuid4()
        mocker.patch("uuid.uuid4", return_value=key)
        resp = await client.post(self.transfer_url.format(applet_id=applet_one.id), data=data)
        assert resp.status_code == http.HTTPStatus.OK

        client.login(lucy)
        # Transfer sent for applet_one
        resp = await client.delete(self.response_url.format(applet_id=applet_two.id, key=key))
        assert resp.status_code == http.HTTPStatus.FORBIDDEN
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == PermissionsError.message
