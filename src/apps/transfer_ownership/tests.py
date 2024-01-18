import re

from apps.applets.domain import Role
from apps.invitations.errors import ManagerInvitationExist
from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from infrastructure.database import rollback


class TestTransfer(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "transfer_ownership/fixtures/transfers.json",
        "invitations/fixtures/invitations.json",
        "themes/fixtures/themes.json",
    ]

    login_url = "/auth/login"
    transfer_url = "/applets/{applet_id}/transferOwnership"
    response_url = "/applets/{applet_id}/transferOwnership/{key}"
    applet_details_url = "/applets/{applet_id}"
    invite_manager_url = "/invitations/{applet_id}/managers"
    invite_accept_url = "/invitations/{key}/accept"
    workspace_applet_managers_list = (
        "/workspaces/{owner_id}/applets/{applet_id}/managers"
    )
    applet_encryption_url = f"{applet_details_url}/encryption"

    @rollback
    async def test_initiate_transfer(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = {"email": "lucy@gmail.com"}

        response = await self.client.post(
            self.transfer_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=data,
        )

        assert response.status_code == 200
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [data["email"]]
        assert TestMail.mails[0].subject == "Transfer ownership of an applet"

    @rollback
    async def test_initiate_transfer_fail(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = {"email": "aloevdamirkhon@gmail.com"}

        response = await self.client.post(
            self.transfer_url.format(
                applet_id="00000000-0000-0000-0000-000000000012"
            ),
            data=data,
        )

        assert response.status_code == 404, response.json()

    @rollback
    async def test_decline_transfer(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await self.client.delete(
            self.response_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == 204

    @rollback
    async def test_decline_wrong_transfer(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await self.client.delete(
            self.response_url.format(
                applet_id="00000000-0000-0000-0000-000000000000",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == 404

    @rollback
    async def test_re_decline_transfer(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await self.client.delete(
            self.response_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == 204

        response = await self.client.delete(
            self.response_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == 404

    @rollback
    async def test_accept_transfer(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await self.client.post(
            self.response_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == 200

    @rollback
    async def test_accept_wrong_transfer(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await self.client.post(
            self.response_url.format(
                applet_id="00000000-0000-0000-0000-000000000000",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == 404

    @rollback
    async def test_re_accept_transfer(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await self.client.post(
            self.response_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == 200

        response = await self.client.post(
            self.response_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )

        assert response.status_code == 404

    @rollback
    async def test_accept_transfer_report_settings_are_kept(self):
        report_settings_keys = (
            "reportServerIp",
            "reportPublicKey",
            "reportRecipients",
            "reportEmailBody",
            "reportIncludeUserId",
            "reportIncludeCaseId",
        )
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        resp = await self.client.get(
            self.applet_details_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert resp.status_code == 200
        resp_data = resp.json()["result"]
        # Fot this test all report settings are set for applet
        for key in report_settings_keys:
            assert resp_data[key]

        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        response = await self.client.post(
            self.response_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                key="6a3ab8e6-f2fa-49ae-b2db-197136677da7",
            ),
        )
        assert response.status_code == 200

        resp = await self.client.get(
            self.applet_details_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )
        assert resp.status_code == 200
        resp_data = resp.json()["result"]
        # After accept transfership all report settings must be kept
        for key in report_settings_keys:
            assert resp_data[key]

    @rollback
    async def test_reinvite_manager_after_transfer(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.MANAGER,
            language="en",
        )
        # send manager invite
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=request_data,
        )
        assert response.status_code == 200
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [request_data["email"]]

        # accept manager invite
        await self.client.login(self.login_url, "patric@gmail.com", "Test1234")
        key = response.json()["result"]["key"]
        response = await self.client.post(
            self.invite_accept_url.format(key=key)
        )
        assert response.status_code == 200

        # transfer ownership to mike@gmail.com
        # initiate transfer
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = {"email": "mike@gmail.com"}

        response = await self.client.post(
            self.transfer_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=data,
        )

        assert response.status_code == 200

        assert len(TestMail.mails) == 2
        assert TestMail.mails[0].recipients == [data["email"]]
        assert TestMail.mails[0].subject == "Transfer ownership of an applet"
        body = TestMail.mails[0].body
        regex = r"\bkey=[0-9a-fA-F]{8}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{4}\b-[0-9a-fA-F]{12}&action=accept"  # noqa: E501
        key = re.findall(regex, body)
        key = key[0][4:-14]

        # accept transfer
        await self.client.login(self.login_url, "mike@gmail.com", "Test1234")
        response = await self.client.post(
            self.response_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
                key=key,
            ),
        )
        assert response.status_code == 200

        # check managers list
        response = await self.client.get(
            self.workspace_applet_managers_list.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa4",
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1",
            ),
        )

        assert response.status_code == 200
        result = response.json()["result"]
        email_role_map = dict()
        for res in result:
            email_role_map[res["email"]] = res["roles"]
        emails = list(email_role_map.keys())

        assert "mike@gmail.com" in emails
        assert Role.OWNER in email_role_map["mike@gmail.com"]

        assert "patric@gmail.com" in emails
        assert Role.MANAGER in email_role_map["patric@gmail.com"]

        # try sending manager invite,
        request_data = dict(
            email="patric@gmail.com",
            first_name="Patric",
            last_name="Daniel",
            role=Role.MANAGER,
            language="en",
        )
        response = await self.client.post(
            self.invite_manager_url.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            ),
            data=request_data,
        )
        assert response.status_code == ManagerInvitationExist.status_code
        assert (
            response.json()["result"][0]["message"]
            == ManagerInvitationExist.message
        )
