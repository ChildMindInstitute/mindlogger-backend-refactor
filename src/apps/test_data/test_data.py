import uuid

from apps.shared.test import BaseTest


class TestData(BaseTest):
    login_url = "/auth/login"
    generating_url = "/data"
    generate_applet_url = f"{generating_url}/generate_applet"
    applet_list_url = "applets"

    async def test_generate_applet(self, client, user):
        await client.login(self.login_url, user.email_encrypted, "Test1234!")

        response = await client.post(
            self.generate_applet_url,
            data=dict(
                encryption=dict(
                    public_key=uuid.uuid4().hex,
                    prime=uuid.uuid4().hex,
                    base=uuid.uuid4().hex,
                    account_id=str(uuid.uuid4()),
                ),
            ),
        )

        assert response.status_code == 201, response.json()
        response = await client.get(self.applet_list_url)
        assert response.status_code == 200
        assert response.json()["count"] == 1
