import http

from apps.activities.errors import PeriodIsRequiredError
from apps.applets.domain.applet_full import AppletFull
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User


class TestSettings(BaseTest):
    login_url = "/auth/login"
    applet_url = "applets/{applet_id}"
    data_retention = applet_url + "/retentions"

    async def test_applet_set_data_retention(self, client: TestClient, applet_one: AppletFull, tom: User):
        client.login(tom)

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

    async def test_applet_set_data_retention_for_indefinite(
        self, client: TestClient, applet_one: AppletFull, tom: User
    ):
        client.login(tom)

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

    async def test_applet_set_data_retention_for_indefinite_fail(
        self, client: TestClient, applet_one: AppletFull, tom: User
    ):
        client.login(tom)

        retention_data = dict(
            retention="days",
        )

        response = await client.post(
            self.data_retention.format(applet_id=applet_one.id),
            data=retention_data,
        )
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        assert response.json()["result"][0]["message"] == PeriodIsRequiredError.message
