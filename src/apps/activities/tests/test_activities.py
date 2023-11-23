from apps.shared.test import BaseTest
from infrastructure.database import rollback


class TestActivities(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "themes/fixtures/themes.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_user_accesses.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_items.json",
    ]

    login_url = "/auth/login"
    activity_detail = "/activities/{pk}"
    activities_applet = "/activities/applet/{applet_id}"
    public_activity_detail = "public/activities/{pk}"

    @rollback
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

    @rollback
    async def test_activities_applet(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        response = await self.client.get(
            self.activities_applet.format(
                applet_id="92917a56-d586-4613-b7aa-991f2c4b15b1"
            )
        )

        assert response.status_code == 200, response.json()
        result = response.json()["result"]

        assert len(result["activitiesDetails"]) == 1
        assert (
            result["activitiesDetails"][0]["id"]
            == "09e3dbf0-aefb-4d0e-9177-bdb321bf3611"
        )
        assert result["activitiesDetails"][0]["name"] == "PHQ2"
        assert result["activitiesDetails"][0]["description"] == "PHQ2 en"
        assert result["activitiesDetails"][0]["splashScreen"] == ""
        assert result["activitiesDetails"][0]["image"] == ""
        assert result["activitiesDetails"][0]["showAllAtOnce"] is False
        assert result["activitiesDetails"][0]["isSkippable"] is False
        assert result["activitiesDetails"][0]["isReviewable"] is False
        assert result["activitiesDetails"][0]["isHidden"] is False
        assert result["activitiesDetails"][0]["responseIsEditable"] is False
        assert result["activitiesDetails"][0]["order"] == 1

        assert len(result["activitiesDetails"][0]["items"]) == 2
        items = sorted(
            result["activitiesDetails"][0]["items"], key=lambda x: x["id"]
        )
        assert items[0]["id"] == "a18d3409-2c96-4a5e-a1f3-1c1c14be0011"
        assert (
            items[0]["question"]
            == "Little interest or pleasure in doing things?"
        )
        assert items[0]["responseType"] == "singleSelect"
        assert items[0]["name"] == "test1"
        assert items[0]["isHidden"] is None
        assert items[0]["conditionalLogic"] is None
        assert items[0]["allowEdit"] is None
        assert items[0]["responseValues"]["paletteName"] is None
        assert len(items[0]["responseValues"]["options"]) == 4
        options_0 = sorted(
            items[0]["responseValues"]["options"], key=lambda x: x["id"]
        )
        assert options_0[0]["id"] == "2ba4bb83-ed1c-4140-a225-c2c9b4db66d2"
        assert options_0[0]["text"] == "Not at all"
        assert options_0[0]["image"] is None
        assert options_0[0]["score"] is None
        assert options_0[0]["tooltip"] is None
        assert options_0[0]["isHidden"] is False
        assert options_0[0]["color"] is None
        assert options_0[0]["alert"] is None
        assert options_0[0]["value"] == 0
        assert options_0[1]["id"] == "2ba4bb83-ed1c-4140-a225-c2c9b4db66d3"
        assert options_0[1]["text"] == "Several days"
        assert options_0[1]["image"] is None
        assert options_0[1]["score"] is None
        assert options_0[1]["tooltip"] is None
        assert options_0[1]["isHidden"] is False
        assert options_0[1]["color"] is None
        assert options_0[1]["alert"] is None
        assert options_0[1]["value"] == 1
        assert options_0[2]["id"] == "2ba4bb83-ed1c-4140-a225-c2c9b4db66d4"
        assert options_0[2]["text"] == "More than half the days"
        assert options_0[2]["image"] is None
        assert options_0[2]["score"] is None
        assert options_0[2]["tooltip"] is None
        assert options_0[2]["isHidden"] is False
        assert options_0[2]["color"] is None
        assert options_0[2]["alert"] is None
        assert options_0[2]["value"] == 2
        assert options_0[3]["id"] == "2ba4bb83-ed1c-4140-a225-c2c9b4db66d5"
        assert options_0[3]["text"] == "Nearly every day"
        assert options_0[3]["image"] is None
        assert options_0[3]["score"] is None
        assert options_0[3]["tooltip"] is None
        assert options_0[3]["isHidden"] is False
        assert options_0[3]["color"] is None
        assert options_0[3]["alert"] is None
        assert options_0[3]["value"] == 3
        assert items[0]["config"]["removeBackButton"] is False
        assert items[0]["config"]["skippableItem"] is False
        assert items[0]["config"]["randomizeOptions"] is False
        assert items[0]["config"]["timer"] == 0
        assert items[0]["config"]["addScores"] is False
        assert items[0]["config"]["setAlerts"] is False
        assert items[0]["config"]["addTooltip"] is False
        assert items[0]["config"]["setPalette"] is False
        assert items[0]["config"]["addTokens"] is None
        assert (
            items[0]["config"]["additionalResponseOption"]["textInputOption"]
            is False
        )
        assert (
            items[0]["config"]["additionalResponseOption"]["textInputRequired"]
            is False
        )

        assert items[1]["id"] == "a18d3409-2c96-4a5e-a1f3-1c1c14be0012"
        assert items[1]["question"] == "Feeling down, depressed, or hopeless?"
        assert items[1]["responseType"] == "singleSelect"
        assert items[1]["name"] == "test"
        assert items[1]["isHidden"] is None
        assert items[1]["conditionalLogic"] is None
        assert items[1]["allowEdit"] is None
        assert items[1]["responseValues"]["paletteName"] is None
        assert len(items[1]["responseValues"]["options"]) == 4
        options_1 = sorted(
            items[1]["responseValues"]["options"], key=lambda x: x["id"]
        )
        assert options_1[0]["id"] == "2ba4bb83-ed1c-4140-a225-c2c9b4db66e2"
        assert options_1[0]["text"] == "Not at all"
        assert options_1[0]["image"] is None
        assert options_1[0]["score"] is None
        assert options_1[0]["tooltip"] is None
        assert options_1[0]["isHidden"] is False
        assert options_1[0]["color"] is None
        assert options_1[0]["alert"] is None
        assert options_1[0]["value"] == 0
        assert options_1[1]["id"] == "2ba4bb83-ed1c-4140-a225-c2c9b4db66e3"
        assert options_1[1]["text"] == "Several days"
        assert options_1[1]["image"] is None
        assert options_1[1]["score"] is None
        assert options_1[1]["tooltip"] is None
        assert options_1[1]["isHidden"] is False
        assert options_1[1]["color"] is None
        assert options_1[1]["alert"] is None
        assert options_1[1]["value"] == 1
        assert options_1[2]["id"] == "2ba4bb83-ed1c-4140-a225-c2c9b4db66e4"
        assert options_1[2]["text"] == "More than half the days"
        assert options_1[2]["image"] is None
        assert options_1[2]["score"] is None
        assert options_1[2]["tooltip"] is None
        assert options_1[2]["isHidden"] is False
        assert options_1[2]["color"] is None
        assert options_1[2]["alert"] is None
        assert options_1[2]["value"] == 2
        assert options_1[3]["id"] == "2ba4bb83-ed1c-4140-a225-c2c9b4db66e5"
        assert options_1[3]["text"] == "Nearly every day"
        assert options_1[3]["image"] is None
        assert options_1[3]["score"] is None
        assert options_1[3]["tooltip"] is None
        assert options_1[3]["isHidden"] is False
        assert options_1[3]["color"] is None
        assert options_1[3]["alert"] is None
        assert options_1[3]["value"] == 3
        assert items[1]["config"]["removeBackButton"] is False
        assert items[1]["config"]["skippableItem"] is False
        assert items[1]["config"]["randomizeOptions"] is False
        assert items[1]["config"]["timer"] == 0
        assert items[1]["config"]["addScores"] is False
        assert items[1]["config"]["setAlerts"] is False
        assert items[1]["config"]["addTooltip"] is False
        assert items[1]["config"]["setPalette"] is False
        assert items[1]["config"]["addTokens"] is None
        assert (
            items[1]["config"]["additionalResponseOption"]["textInputOption"]
            is False
        )
        assert (
            items[1]["config"]["additionalResponseOption"]["textInputRequired"]
            is False
        )

        assert result["activitiesDetails"][0]["scoresAndReports"] is None

        assert (
            result["appletDetail"]["id"]
            == "92917a56-d586-4613-b7aa-991f2c4b15b1"
        )
        assert result["appletDetail"]["displayName"] == "Applet 1"
        assert result["appletDetail"]["version"] == "1.0.0"
        assert (
            result["appletDetail"]["description"]
            == "Patient Health Questionnaire"
        )
        assert (
            result["appletDetail"]["about"] == "Patient Health Questionnaire"
        )
        assert result["appletDetail"]["image"] == ""
        assert result["appletDetail"]["watermark"] == ""
        assert (
            result["appletDetail"]["theme"]["id"]
            == "3e31a64e-449f-4788-8516-eca7809f1a41"
        )
        assert result["appletDetail"]["theme"]["name"] == "Theme 1"
        assert result["appletDetail"]["theme"]["logo"] == "logo1.jpg"
        assert (
            result["appletDetail"]["theme"]["backgroundImage"] == "image1.jpg"
        )
        assert result["appletDetail"]["theme"]["primaryColor"] == "#000"
        assert result["appletDetail"]["theme"]["secondaryColor"] == "#f00"
        assert result["appletDetail"]["theme"]["tertiaryColor"] == "#fff"
        assert len(result["appletDetail"]["activities"]) == 1
        assert (
            result["appletDetail"]["activities"][0]["id"]
            == "09e3dbf0-aefb-4d0e-9177-bdb321bf3611"
        )
        assert result["appletDetail"]["activities"][0]["name"] == "PHQ2"
        assert (
            result["appletDetail"]["activities"][0]["description"] == "PHQ2 en"
        )
        assert result["appletDetail"]["activities"][0]["image"] == ""
        assert result["appletDetail"]["activities"][0]["isReviewable"] is False
        assert result["appletDetail"]["activities"][0]["isSkippable"] is False
        assert (
            result["appletDetail"]["activities"][0]["showAllAtOnce"] is False
        )
        assert result["appletDetail"]["activities"][0]["isHidden"] is False
        assert (
            result["appletDetail"]["activities"][0]["responseIsEditable"]
            is False
        )
        assert result["appletDetail"]["activities"][0]["order"] == 1
        assert result["appletDetail"]["activities"][0]["splashScreen"] == ""
        assert result["appletDetail"]["activityFlows"] == []

        assert result["respondentMeta"] == {"nickname": "respondent Jane Doe"}

    @rollback
    async def test_public_activity_detail(self):
        response = await self.client.get(
            self.public_activity_detail.format(
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
