from apps.shared.test import BaseTest


class TestActivities(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_items.json",
    ]

    login_url = "/auth/login"
    activity_detail = "/activities/{pk}"

    async def test_activity_detail(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(
            self.activity_detail.format(
                pk="09e3dbf0-aefb-4d0e-9177-bdb321bf3611"
            )
        )

        assert response.status_code == 200, response.json()
        result = response.json()["result"]
        assert result["id"] == "09e3dbf0-aefb-4d0e-9177-bdb321bf3611"
        assert result["name"] == "PHQ2"
        assert result["description"] == "PHQ2 en"
        assert len(result["items"]) == 2
        assert (
            result["items"][0]["question"]
            == "Little interest or pleasure in doing things?"
        )
        assert (
            result["items"][1]["question"]
            == "Feeling down, depressed, or hopeless?"
        )
