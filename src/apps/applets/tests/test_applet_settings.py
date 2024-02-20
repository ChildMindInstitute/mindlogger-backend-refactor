import http

from apps.shared.test import BaseTest


class TestSettings(BaseTest):
    login_url = "/auth/login"
    applet_url = "applets/{applet_id}"
    data_retention = applet_url + "/retentions"

    async def test_applet_set_data_retention(self, client, applet_one):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        retention_data = dict(
            period=1,
            retention="days",
        )

        response = await client.post(
            self.data_retention.format(applet_id=applet_one.id),
            data=retention_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        response = await client.get(self.applet_url.format(applet_id=applet_one.id))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["retentionPeriod"] == retention_data["period"]
        assert response.json()["result"]["retentionType"] == retention_data["retention"]

    async def test_applet_set_data_retention_for_indefinite(self, client, applet_one):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        retention_data = dict(
            retention="indefinitely",
        )

        response = await client.post(
            self.data_retention.format(applet_id=applet_one.id),
            data=retention_data,
        )
        assert response.status_code == http.HTTPStatus.OK

        response = await client.get(self.applet_url.format(applet_id=applet_one.id))
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["result"]["retentionPeriod"] is None
        assert response.json()["result"]["retentionType"] == retention_data["retention"]

    async def test_applet_set_data_retention_for_indefinite_fail(self, client, applet_one):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        retention_data = dict(
            retention="days",
        )

        response = await client.post(
            self.data_retention.format(applet_id=applet_one.id),
            data=retention_data,
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
