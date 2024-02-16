import http
from typing import cast

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.response_type_config import SingleSelectionConfig
from apps.activities.domain.response_values import SingleSelectionValues
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.applet_link import CreateAccessLink
from apps.applets.service.applet import AppletService
from apps.shared.enums import Language
from apps.themes.domain import Theme
from apps.users.domain import User


@pytest.fixture
async def applet_one_with_public_link(session: AsyncSession, applet_one: AppletFull, tom):
    srv = AppletService(session, tom.id)
    await srv.create_access_link(applet_one.id, CreateAccessLink(require_login=False))
    applet = await srv.get_full_applet(applet_one.id)
    assert applet.link is not None
    return applet


class TestActivities:
    login_url = "/auth/login"
    activity_detail = "/activities/{pk}"
    activities_applet = "/activities/applet/{applet_id}"
    public_activity_detail = "public/activities/{pk}"

    async def test_activity_detail(self, client, applet_one: AppletFull):
        activity = applet_one.activities[0]
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.get(self.activity_detail.format(pk=activity.id))

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert result["id"] == str(activity.id)
        assert result["name"] == activity.name
        assert result["description"] == activity.description[Language.ENGLISH]
        assert len(result["items"]) == 1
        assert result["items"][0]["question"] == activity.items[0].question[Language.ENGLISH]

    async def test_activities_applet(self, client, applet_one: AppletFull, default_theme: Theme, tom: User):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")
        response = await client.get(self.activities_applet.format(applet_id=applet_one.id))

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]

        activity = applet_one.activities[0]
        assert len(result["activitiesDetails"]) == 1
        assert result["activitiesDetails"][0]["id"] == str(activity.id)
        assert result["activitiesDetails"][0]["name"] == activity.name
        assert result["activitiesDetails"][0]["description"] == activity.description[Language.ENGLISH]
        assert result["activitiesDetails"][0]["splashScreen"] == activity.splash_screen
        assert result["activitiesDetails"][0]["image"] == activity.image
        assert result["activitiesDetails"][0]["showAllAtOnce"] == activity.show_all_at_once
        assert result["activitiesDetails"][0]["isSkippable"] == activity.is_skippable
        assert result["activitiesDetails"][0]["isReviewable"] == activity.is_reviewable
        assert result["activitiesDetails"][0]["isHidden"] == activity.is_hidden
        assert result["activitiesDetails"][0]["responseIsEditable"] == activity.response_is_editable
        assert result["activitiesDetails"][0]["order"] == 1

        items = result["activitiesDetails"][0]["items"]
        activity_item = activity.items[0]
        assert len(items) == 1
        assert len(items) == len(activity.items)
        item = items[0]
        assert item["id"] == str(activity_item.id)
        assert item["question"] == activity_item.question[Language.ENGLISH]
        assert item["responseType"] == activity_item.response_type
        assert item["name"] == activity_item.name
        assert item["isHidden"] == activity_item.is_hidden
        assert item["conditionalLogic"] == activity_item.conditional_logic
        assert item["allowEdit"] == activity_item.allow_edit
        assert len(item["responseValues"]["options"]) == 1
        option = item["responseValues"]["options"][0]
        activity_item.response_values = cast(SingleSelectionValues, activity_item.response_values)
        assert item["responseValues"]["paletteName"] == activity_item.response_values.palette_name
        activity_item_option = activity_item.response_values.options[0]
        assert option["id"] == activity_item_option.id
        assert option["text"] == activity_item_option.text
        assert option["image"] == activity_item_option.image
        assert option["score"] == activity_item_option.score
        assert option["tooltip"] == activity_item_option.tooltip
        assert option["isHidden"] == activity_item_option.is_hidden
        assert option["color"] == activity_item_option.color
        assert option["alert"] == activity_item_option.alert
        assert option["value"] == activity_item_option.value
        config = item["config"]
        activity_item.config = cast(SingleSelectionConfig, activity_item.config)
        assert config["removeBackButton"] == activity_item.config.remove_back_button
        assert config["skippableItem"] == activity_item.config.skippable_item
        assert config["randomizeOptions"] == activity_item.config.randomize_options
        assert config["timer"] == activity_item.config.timer
        assert config["addScores"] == activity_item.config.add_scores
        assert config["setAlerts"] == activity_item.config.set_alerts
        assert config["addTooltip"] == activity_item.config.add_tooltip
        assert config["setPalette"] == activity_item.config.set_palette
        assert config["addTokens"] == activity_item.config.add_tokens
        assert (
            config["additionalResponseOption"]["textInputOption"]
            == activity_item.config.additional_response_option.text_input_option
        )
        assert (
            config["additionalResponseOption"]["textInputRequired"]
            == activity_item.config.additional_response_option.text_input_required
        )

        assert result["activitiesDetails"][0]["scoresAndReports"] == activity.scores_and_reports

        assert result["appletDetail"]["id"] == str(applet_one.id)
        assert result["appletDetail"]["displayName"] == applet_one.display_name
        assert result["appletDetail"]["version"] == applet_one.version
        assert result["appletDetail"]["description"] == applet_one.description.get(Language.ENGLISH, "")
        assert result["appletDetail"]["about"] == applet_one.about.get(Language.ENGLISH, "")
        assert result["appletDetail"]["image"] == applet_one.image
        assert result["appletDetail"]["watermark"] == applet_one.watermark
        assert result["appletDetail"]["theme"]["id"] == str(applet_one.theme_id)
        assert result["appletDetail"]["theme"]["name"] == default_theme.name
        assert result["appletDetail"]["theme"]["logo"] == default_theme.logo
        assert result["appletDetail"]["theme"]["backgroundImage"] == default_theme.background_image
        assert result["appletDetail"]["theme"]["primaryColor"] == str(default_theme.primary_color)[:4].lower()
        assert result["appletDetail"]["theme"]["secondaryColor"] == str(default_theme.secondary_color)[:4].lower()
        assert result["appletDetail"]["theme"]["tertiaryColor"] == str(default_theme.tertiary_color)[:4].lower()
        assert len(result["appletDetail"]["activities"]) == 1
        assert result["appletDetail"]["activities"][0]["id"] == str(activity.id)
        assert result["appletDetail"]["activities"][0]["name"] == activity.name
        assert result["appletDetail"]["activities"][0]["description"] == activity.description[Language.ENGLISH]
        assert result["appletDetail"]["activities"][0]["image"] == activity.image
        assert result["appletDetail"]["activities"][0]["isReviewable"] == activity.is_reviewable
        assert result["appletDetail"]["activities"][0]["isSkippable"] == activity.is_skippable
        assert result["appletDetail"]["activities"][0]["showAllAtOnce"] == activity.show_all_at_once
        assert result["appletDetail"]["activities"][0]["isHidden"] == activity.is_hidden
        assert result["appletDetail"]["activities"][0]["responseIsEditable"] == activity.response_is_editable
        assert result["appletDetail"]["activities"][0]["order"] == activity.order
        assert result["appletDetail"]["activities"][0]["splashScreen"] == activity.splash_screen
        assert result["appletDetail"]["activityFlows"] == []

        assert result["respondentMeta"] == {"nickname": f"{tom.first_name} {tom.last_name}"}

    async def test_public_activity_detail(self, client, applet_one_with_public_link: AppletFull):
        activity = applet_one_with_public_link.activities[0]
        response = await client.get(self.public_activity_detail.format(pk=activity.id))

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert result["id"] == str(activity.id)
        assert result["name"] == activity.name
        assert result["description"] == activity.description[Language.ENGLISH]
        assert len(result["items"]) == len(activity.items)
        assert result["items"][0]["question"] == activity.items[0].question[Language.ENGLISH]
