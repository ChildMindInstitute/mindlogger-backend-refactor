import http

from apps.shared.test import BaseTest


class TestAlert(BaseTest):
    fixtures = [
        "alerts/fixtures/alerts.json",
        "workspaces/fixtures/workspaces.json",
    ]

    login_url = "/auth/login"
    alert_list_url = "/alerts"
    watch_alert_url = "/alerts/{alert_id}/is_watched"

    async def test_all_alerts(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.get(self.alert_list_url)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 2

    async def test_watch_alert(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.post(self.watch_alert_url.format(alert_id="6f794861-0ff6-4c39-a3ed-602fd4e22c58"))
        assert response.status_code == http.HTTPStatus.OK

        response = await client.get(self.alert_list_url)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 2
        assert response.json()["result"][0]["isWatched"] is True
