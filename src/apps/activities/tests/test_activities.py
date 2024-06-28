import http
import json
import uuid
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
    activities_flows_applet = "/activities/flows/applet/{applet_id}"
    public_activity_detail = "public/activities/{pk}"
    answer_url = "/answers"
    applet_update_url = "applets/{applet_id}"

    async def test_activity_detail(self, client, applet_one: AppletFull, tom: User):
        activity = applet_one.activities[0]
        client.login(tom)
        response = await client.get(self.activity_detail.format(pk=activity.id))

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]
        assert result["id"] == str(activity.id)
        assert result["name"] == activity.name
        assert result["description"] == activity.description[Language.ENGLISH]
        assert len(result["items"]) == 1
        assert result["items"][0]["question"] == activity.items[0].question[Language.ENGLISH]

    async def test_activities_applet(
        self, client, applet_one: AppletFull, default_theme: Theme, tom: User, tom_applet_one_subject
    ):
        client.login(tom)
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

        assert result["respondentMeta"] == {
            "nickname": f"{tom.first_name} {tom.last_name}",
            "tag": tom_applet_one_subject.tag,
        }

    async def test_activities_flows_applet(
        self, client, applet_activity_flow: AppletFull, default_theme: Theme, tom: User
    ):
        client.login(tom)
        response = await client.get(self.activities_flows_applet.format(applet_id=applet_activity_flow.id))

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]

        activity = applet_activity_flow.activities[0]
        flow = applet_activity_flow.activity_flows[0]
        assert len(result["details"]) == 2

        assert result["details"][0]["id"] == str(activity.id)
        assert result["details"][0]["name"] == activity.name
        assert result["details"][0]["description"] == activity.description[Language.ENGLISH]
        assert result["details"][0]["splashScreen"] == activity.splash_screen
        assert result["details"][0]["image"] == activity.image
        assert result["details"][0]["showAllAtOnce"] == activity.show_all_at_once
        assert result["details"][0]["isSkippable"] == activity.is_skippable
        assert result["details"][0]["isReviewable"] == activity.is_reviewable
        assert result["details"][0]["isHidden"] == activity.is_hidden
        assert result["details"][0]["responseIsEditable"] == activity.response_is_editable
        assert result["details"][0]["order"] == 1
        assert result["details"][0]["type"] == "activity"

        items = result["details"][0]["items"]
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

        assert result["details"][0]["scoresAndReports"] == activity.scores_and_reports

        assert activity.id == flow.items[0].activity_id
        assert result["details"][1]["name"] == flow.name
        assert result["details"][1]["description"] == flow.description
        assert result["details"][1]["type"] == "activityFlow"

        items = result["details"][1]["items"]
        flow_item = flow.items[0]
        assert len(items) == 1
        assert len(items) == len(flow.items)
        item = items[0]
        assert item["id"] == str(flow_item.id)
        assert item["activityId"] == str(flow_item.activity_id)
        assert item["order"] == flow_item.order

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

    # Get only applet activies with submitted answers
    async def test_activities_applet_has_submitted(
        self, client, applet_one: AppletFull, default_theme: Theme, tom: User
    ):
        client.login(tom)

        # Create answer
        create_data = dict(
            submit_id=str(uuid.uuid4()),
            applet_id=str(applet_one.id),
            version=applet_one.version,
            activity_id=str(applet_one.activities[0].id),
            answer=dict(
                user_public_key="user key",
                events=json.dumps(dict(events=["event1", "event2"])),
                answer=json.dumps(
                    dict(
                        value=str(uuid.uuid4()),
                        additional_text=None,
                    )
                ),
                item_ids=[str(applet_one.activities[0].items[0].id)],
                scheduled_time=1690188679657,
                start_time=1690188679657,
                end_time=1690188731636,
            ),
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        response = await client.get(self.activities_applet.format(applet_id=applet_one.id), {"hasSubmitted": True})

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]

        activity = applet_one.activities[0]
        assert len(result["activitiesDetails"]) == 1
        assert result["activitiesDetails"][0]["id"] == str(activity.id)
        assert result["activitiesDetails"][0]["name"] == activity.name

    # Get only applet activies with score
    async def test_activities_applet_has_score(self, client, applet_one: AppletFull, default_theme: Theme, tom: User):
        client.login(tom)

        create_data = dict(
            display_name="User daily behave",
            encryption=dict(
                public_key=uuid.uuid4().hex,
                prime=uuid.uuid4().hex,
                base=uuid.uuid4().hex,
                account_id=str(uuid.uuid4()),
            ),
            description=dict(
                en="Understand users behave",
                fr="Comprendre le comportement des utilisateurs",
            ),
            about=dict(
                en="Understand users behave",
                fr="Comprendre le comportement des utilisateurs",
            ),
            activities=[
                dict(
                    name="Morning activity",
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            name="activity_item_singleselect",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="singleSelect",
                            response_values=dict(
                                options=[
                                    {
                                        "text": "Good",
                                        "score": 1,
                                        "id": "25e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                        "value": "1",
                                    },
                                    {
                                        "text": "Bad",
                                        "score": 2,
                                        "id": "26e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                        "value": "2",
                                    },
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=True,
                                set_alerts=False,
                                timer=0,
                                add_tooltip=False,
                                set_palette=False,
                                randomize_options=False,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                    ],
                )
            ],
            activity_flows=[
                dict(
                    name="Morning questionnaire",
                    description=dict(
                        en="Understand how was the morning",
                        fr="Understand how was the morning",
                    ),
                    items=[dict(activity_key="577dbbda-3afc-" "4962-842b-8d8d11588bfe")],
                )
            ],
        )

        response = await client.put(self.applet_update_url.format(applet_id=applet_one.id), data=create_data)
        assert response.status_code == http.HTTPStatus.OK

        response = await client.get(self.activities_applet.format(applet_id=applet_one.id), {"hasScore": True})

        assert response.status_code == http.HTTPStatus.OK

        result = response.json()["result"]
        assert len(result["activitiesDetails"]) == 1
        items = result["activitiesDetails"][0]["items"]
        assert len(items) == 1
        item = items[0]
        assert len(item["responseValues"]["options"]) == 2
        option = item["responseValues"]["options"][0]
        assert option["score"] > 0
