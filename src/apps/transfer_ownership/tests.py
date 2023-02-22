from apps.mailing.services import TestMail
from apps.shared.test import BaseTest
from infrastructure.database import transaction


class TestTransfer(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "transfer_ownership/fixtures/transfers.json",
    ]

    login_url = "/auth/login"
    transfer_url = "/applets/{applet_id}/transferOwnership"
    response_url = "/applets/{applet_id}/transferOwnership/{key}"

    @transaction.rollback
    async def test_initiate_transfer(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        data = {"email": "aloevdamirkhon@gmail.com"}

        response = await self.client.post(
            self.transfer_url.format(applet_id=1), data=data
        )

        assert response.status_code == 200
        assert len(TestMail.mails) == 1
        assert TestMail.mails[0].recipients == [data["email"]]
        TestMail.clear_mails()

    @transaction.rollback
    async def test_decline_transfer(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        data = {"accepted": False}
        response = await self.client.post(
            self.response_url.format(
                applet_id=1, key="6a3ab8e6-f2fa-49ae-b2db-197136677da7"
            ),
            data=data,
        )

        assert response.status_code == 200

    @transaction.rollback
    async def test_accept_transfer(self):
        await self.client.login(self.login_url, "lucy@gmail.com", "Test123")
        data = {"accepted": True}
        response = await self.client.post(
            self.response_url.format(
                applet_id=1, key="6a3ab8e6-f2fa-49ae-b2db-197136677da7"
            ),
            data=data,
        )

        assert response.status_code == 200
