import http
import json
import uuid
from typing import AsyncGenerator, cast

import pytest
from _pytest.config import Config
from pytest_mock import MockerFixture
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.activity import ActivityOrFlowStatusEnum
from apps.activities.domain.activity_create import ActivityCreate
from apps.activities.domain.activity_update import ActivityUpdate
from apps.activities.domain.response_type_config import SingleSelectionConfig
from apps.activities.domain.response_values import SingleSelectionValues
from apps.activities.services.activity import ActivityService
from apps.activity_assignments.domain.assignments import ActivityAssignmentCreate
from apps.activity_assignments.service import ActivityAssignmentService
from apps.activity_flows.domain.flow_update import ActivityFlowItemUpdate, FlowUpdate
from apps.activity_flows.service.flow import FlowService
from apps.answers.domain import AppletAnswerCreate
from apps.answers.service import AnswerService
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.applet_link import CreateAccessLink
from apps.applets.domain.base import AppletBase
from apps.applets.service.applet import AppletService
from apps.applets.tests.fixtures.applets import _get_or_create_applet
from apps.applets.tests.utils import teardown_applet
from apps.shared.enums import Language
from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import Subject
from apps.themes.domain import Theme
from apps.users.domain import User
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


@pytest.fixture
async def applet_one_with_public_link(session: AsyncSession, applet_one: AppletFull, tom):
    srv = AppletService(session, tom.id)
    await srv.create_access_link(applet_one.id, CreateAccessLink(require_login=False))
    applet = await srv.get_full_applet(applet_one.id)
    assert applet.link is not None
    return applet


@pytest.fixture
async def lucy_applet_one_subject(session: AsyncSession, lucy: User, applet_one_lucy_respondent: AppletFull) -> Subject:
    applet_id = applet_one_lucy_respondent.id
    query = select(SubjectSchema).where(SubjectSchema.user_id == lucy.id, SubjectSchema.applet_id == applet_id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
async def applet_one_user_respondent(session: AsyncSession, applet_one: AppletFull, tom, user) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(user.id, Role.RESPONDENT)
    return applet_one


@pytest.fixture
async def user_applet_one_subject(session: AsyncSession, user: User, applet_one_user_respondent: AppletFull) -> Subject:
    applet_id = applet_one_user_respondent.id
    query = select(SubjectSchema).where(SubjectSchema.user_id == user.id, SubjectSchema.applet_id == applet_id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
async def applet_one_lucy_reviewer(
    session: AsyncSession,
    applet_one: AppletFull,
    mocker: MockerFixture,
    tom: User,
    lucy: User,
    user_applet_one_subject: Subject,
) -> AppletFull:
    mocker.patch(
        "apps.workspaces.service.user_applet_access.UserAppletAccessService._get_default_role_meta",
        return_value={"subjects": [str(user_applet_one_subject.id)]},
    )
    await UserAppletAccessService(session, tom.id, applet_one.id).add_role(lucy.id, Role.REVIEWER)
    return applet_one


@pytest.fixture
async def empty_applet(
    session: AsyncSession,
    tom: User,
    applet_base_data: AppletBase,
    pytestconfig: Config,
) -> AsyncGenerator[AppletFull, None]:
    applet_id = uuid.UUID("92917a56-d586-4613-b7aa-991f2c4b15b0")
    applet_name = "Empty Applet"
    applet_minimal_data = AppletCreate(**applet_base_data.dict(), activities=[], activity_flows=[])
    applet = await _get_or_create_applet(session, applet_name, applet_id, applet_minimal_data, tom.id)
    yield applet
    if not pytestconfig.getoption("--keepdb"):
        await teardown_applet(session, applet.id)


@pytest.fixture
async def empty_applet_lucy_manager(
    session: AsyncSession, empty_applet: AppletFull, tom: User, lucy: User
) -> AppletFull:
    await UserAppletAccessService(session, tom.id, empty_applet.id).add_role(lucy.id, Role.MANAGER)
    return empty_applet


@pytest.fixture
async def applet_activity_flow_lucy_manager(
    session: AsyncSession, applet_activity_flow: AppletFull, tom: User, lucy: User
) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_activity_flow.id).add_role(lucy.id, Role.MANAGER)
    return applet_activity_flow


@pytest.fixture
async def empty_applet_lucy_respondent(
    session: AsyncSession, empty_applet: AppletFull, tom: User, lucy: User
) -> AppletFull:
    await UserAppletAccessService(session, tom.id, empty_applet.id).add_role(lucy.id, Role.RESPONDENT)
    return empty_applet


@pytest.fixture
async def lucy_empty_applet_subject(
    session: AsyncSession, lucy: User, empty_applet_lucy_respondent: AppletFull
) -> Subject:
    applet_id = empty_applet_lucy_respondent.id
    query = select(SubjectSchema).where(SubjectSchema.user_id == lucy.id, SubjectSchema.applet_id == applet_id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
async def empty_applet_user_respondent(session: AsyncSession, empty_applet: AppletFull, tom, user) -> AppletFull:
    await UserAppletAccessService(session, tom.id, empty_applet.id).add_role(user.id, Role.RESPONDENT)
    return empty_applet


@pytest.fixture
async def user_empty_applet_subject(
    session: AsyncSession, user: User, empty_applet_user_respondent: AppletFull
) -> Subject:
    applet_id = empty_applet_user_respondent.id
    query = select(SubjectSchema).where(SubjectSchema.user_id == user.id, SubjectSchema.applet_id == applet_id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
async def applet_activity_flow_lucy_respondent(
    session: AsyncSession, applet_activity_flow: AppletFull, tom: User, lucy: User
) -> AppletFull:
    await UserAppletAccessService(session, tom.id, applet_activity_flow.id).add_role(lucy.id, Role.RESPONDENT)
    return applet_activity_flow


@pytest.fixture
async def lucy_applet_activity_flow_subject(
    session: AsyncSession, lucy: User, applet_activity_flow_lucy_respondent: AppletFull
) -> Subject:
    applet_id = applet_activity_flow_lucy_respondent.id
    query = select(SubjectSchema).where(SubjectSchema.user_id == lucy.id, SubjectSchema.applet_id == applet_id)
    res = await session.execute(query, execution_options={"synchronize_session": False})
    model = res.scalars().one()
    return Subject.from_orm(model)


@pytest.fixture
def answer_create_payload(applet_one: AppletFull):
    return dict(
        submit_id=str(uuid.uuid4()),
        applet_id=str(applet_one.id),
        activity_id=str(applet_one.activities[0].id),
        version=applet_one.version,
        created_at=1690188731636,
        answer=dict(
            user_public_key="user key",
            answer=json.dumps(
                dict(
                    value="2ba4bb83-ed1c-4140-a225-c2c9b4db66d2",
                    additional_text=None,
                )
            ),
            events=json.dumps(dict(events=["event1", "event2"])),
            item_ids=[
                str(applet_one.activities[0].items[0].id),
            ],
            identifier="encrypted_identifier",
            scheduled_time=1690188679657,
            start_time=1690188679657,
            end_time=1690188731636,
            scheduledEventId="eventId",
            localEndDate="2022-10-01",
            localEndTime="12:35:00",
        ),
        alerts=[
            dict(
                activity_item_id=str(applet_one.activities[0].items[0].id),
                message="hello world",
            )
        ],
        client=dict(
            appId="mindlogger-mobile",
            appVersion="0.21.48",
            width=819,
            height=1080,
        ),
    )


class TestActivities:
    login_url = "/auth/login"
    activity_detail = "/activities/{pk}"
    activities_applet = "/activities/applet/{applet_id}"
    activities_flows_applet = "/activities/flows/applet/{applet_id}"
    public_activity_detail = "public/activities/{pk}"
    answer_url = "/answers"
    applet_update_url = "applets/{applet_id}"
    subject_assigned_activities_url = "/activities/applet/{applet_id}/subject/{subject_id}"
    target_assigned_activities_url = "/activities/applet/{applet_id}/target/{subject_id}"

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
        assert config["portraitLayout"] == activity_item.config.portrait_layout
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

    # Get only applet activities with submitted answers
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

    # Get only applet activities with score
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

    async def test_subject_assigned_activities_editor(
        self, client, applet_one_lucy_editor, lucy, lucy_applet_one_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.subject_assigned_activities_url.format(
                applet_id=applet_one_lucy_editor.id, subject_id=lucy_applet_one_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result = response.json()["result"]

        assert result[0]["type"] == "ACCESS_DENIED"
        assert result[0]["message"] == "Access denied to applet."

    async def test_subject_assigned_activities_incorrect_reviewer(
        self, client, applet_one_lucy_reviewer, lucy, lucy_applet_one_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.subject_assigned_activities_url.format(
                applet_id=applet_one_lucy_reviewer.id, subject_id=lucy_applet_one_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result = response.json()["result"]

        assert result[0]["type"] == "ACCESS_DENIED"
        assert result[0]["message"] == "Access denied."

    async def test_subject_assigned_activities_participant(
        self, client, applet_one_lucy_respondent, lucy, lucy_applet_one_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.subject_assigned_activities_url.format(
                applet_id=applet_one_lucy_respondent.id, subject_id=lucy_applet_one_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result = response.json()["result"]

        assert result[0]["type"] == "ACCESS_DENIED"
        assert result[0]["message"] == "Access denied to applet."

    async def test_subject_assigned_activities_participant_other(
        self, client, applet_one_lucy_respondent, lucy, applet_one_user_respondent, user_applet_one_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.subject_assigned_activities_url.format(
                applet_id=applet_one_lucy_respondent.id, subject_id=user_applet_one_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result = response.json()["result"]

        assert result[0]["type"] == "ACCESS_DENIED"
        assert result[0]["message"] == "Access denied to applet."

    async def test_subject_assigned_activities_invalid_applet(
        self, client, applet_one_lucy_manager, lucy, lucy_applet_one_subject
    ):
        client.login(lucy)

        applet_id = uuid.uuid4()

        response = await client.get(
            self.subject_assigned_activities_url.format(applet_id=applet_id, subject_id=lucy_applet_one_subject.id)
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND
        result = response.json()["result"]

        assert result[0]["type"] == "NOT_FOUND"
        assert result[0]["message"] == f"No such applets with id={applet_id}."

    async def test_subject_assigned_activities_invalid_subject(
        self, client, applet_one_lucy_manager, lucy, lucy_applet_one_subject
    ):
        client.login(lucy)

        subject_id = uuid.uuid4()

        response = await client.get(
            self.subject_assigned_activities_url.format(applet_id=applet_one_lucy_manager.id, subject_id=subject_id)
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND
        result = response.json()["result"]

        assert result[0]["type"] == "NOT_FOUND"
        assert result[0]["message"] == f"Subject with id {subject_id} not found"

    async def test_subject_assigned_activities_empty_applet(
        self, client, empty_applet_lucy_manager, lucy, lucy_empty_applet_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.subject_assigned_activities_url.format(
                applet_id=empty_applet_lucy_manager.id, subject_id=lucy_empty_applet_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]

        assert result["activities"] == []
        assert result["activityFlows"] == []

    async def test_subject_assigned_activities_auto_assigned(
        self, client, applet_activity_flow_lucy_manager, lucy, lucy_applet_activity_flow_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.subject_assigned_activities_url.format(
                applet_id=applet_activity_flow_lucy_manager.id, subject_id=lucy_applet_activity_flow_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]

        assert len(result["activityFlows"]) == 1
        assert len(result["activities"]) == 1

        activity = applet_activity_flow_lucy_manager.activities[0]
        activity_result = result["activities"][0]

        assert activity_result["id"] == str(activity.id)
        assert activity_result["name"] == activity.name
        assert activity_result["description"] == activity.description[Language.ENGLISH]
        assert activity_result["autoAssign"] == activity.auto_assign
        assert len(activity_result["items"]) == 1
        assert len(activity_result["assignments"]) == 0

        flow = applet_activity_flow_lucy_manager.activity_flows[0]
        flow_result = result["activityFlows"][0]

        assert flow_result["id"] == str(flow.id)
        assert flow_result["name"] == flow.name
        assert flow_result["description"] == flow.description[Language.ENGLISH]
        assert flow_result["autoAssign"] == flow.auto_assign
        assert len(flow_result["assignments"]) == 0
        assert flow_result["activityIds"][0] == str(flow.items[0].activity_id)

    async def test_subject_assigned_activities_manually_assigned(
        self,
        session,
        client,
        empty_applet_lucy_manager,
        lucy,
        lucy_empty_applet_subject,
        user_empty_applet_subject,
        activity_create_session: ActivityCreate,
    ):
        client.login(lucy)

        activities = await ActivityService(session, lucy.id).update_create(
            empty_applet_lucy_manager.id,
            [
                ActivityUpdate(
                    **activity_create_session.dict(exclude={"name", "auto_assign"}),
                    name="Manual Activity",
                    auto_assign=False,
                )
            ],
        )
        manual_activity = next((activity for activity in activities if activity.name == "Manual Activity"))

        await ActivityAssignmentService(session).create_many(
            empty_applet_lucy_manager.id,
            [
                ActivityAssignmentCreate(
                    activity_id=manual_activity.id,
                    activity_flow_id=None,
                    respondent_subject_id=user_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=manual_activity.id,
                    activity_flow_id=None,
                    respondent_subject_id=user_empty_applet_subject.id,
                    target_subject_id=lucy_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=manual_activity.id,
                    activity_flow_id=None,
                    respondent_subject_id=lucy_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=manual_activity.id,
                    activity_flow_id=None,
                    respondent_subject_id=lucy_empty_applet_subject.id,
                    target_subject_id=lucy_empty_applet_subject.id,
                ),
            ],
        )

        flows = await FlowService(session).update_create(
            empty_applet_lucy_manager.id,
            [
                FlowUpdate(
                    name="Manual Flow",
                    description={Language.ENGLISH: "Manual Flow"},
                    auto_assign=False,
                    items=[ActivityFlowItemUpdate(activity_key=manual_activity.key)],
                )
            ],
            {manual_activity.key: manual_activity.id},
        )

        manual_flow = next((flow for flow in flows if flow.name == "Manual Flow"))

        await ActivityAssignmentService(session).create_many(
            empty_applet_lucy_manager.id,
            [
                ActivityAssignmentCreate(
                    activity_id=None,
                    activity_flow_id=manual_flow.id,
                    respondent_subject_id=user_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=None,
                    activity_flow_id=manual_flow.id,
                    respondent_subject_id=user_empty_applet_subject.id,
                    target_subject_id=lucy_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=None,
                    activity_flow_id=manual_flow.id,
                    respondent_subject_id=lucy_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=None,
                    activity_flow_id=manual_flow.id,
                    respondent_subject_id=lucy_empty_applet_subject.id,
                    target_subject_id=lucy_empty_applet_subject.id,
                ),
            ],
        )

        response = await client.get(
            self.subject_assigned_activities_url.format(
                applet_id=empty_applet_lucy_manager.id, subject_id=user_empty_applet_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]

        assert len(result["activityFlows"]) == 1
        assert len(result["activities"]) == 1

        activity_result = result["activities"][0]

        assert activity_result["id"] == str(manual_activity.id)
        assert activity_result["name"] == manual_activity.name
        assert activity_result["description"] == manual_activity.description[Language.ENGLISH]
        assert activity_result["autoAssign"] is False
        assert len(activity_result["items"]) == 1
        assert len(activity_result["assignments"]) == 3

        activity_assignment = activity_result["assignments"][0]
        assert activity_assignment["activityId"] == str(manual_activity.id)
        assert activity_assignment["respondentSubject"]["id"] == str(user_empty_applet_subject.id)
        assert activity_assignment["targetSubject"]["id"] == str(user_empty_applet_subject.id)

        flow_result = result["activityFlows"][0]

        assert flow_result["id"] == str(manual_flow.id)
        assert flow_result["name"] == manual_flow.name
        assert flow_result["description"] == manual_flow.description[Language.ENGLISH]
        assert flow_result["autoAssign"] is False
        assert len(flow_result["assignments"]) == 3
        assert flow_result["activityIds"][0] == str(manual_flow.items[0].activity_id)

        flow_assignment = flow_result["assignments"][0]
        assert flow_assignment["activityFlowId"] == str(manual_flow.id)
        assert flow_assignment["respondentSubject"]["id"] == str(user_empty_applet_subject.id)
        assert flow_assignment["targetSubject"]["id"] == str(user_empty_applet_subject.id)

    async def test_subject_assigned_activities_auto_and_manually_assigned(
        self,
        session,
        client,
        empty_applet_lucy_manager,
        lucy,
        user_empty_applet_subject,
        activity_create_session: ActivityCreate,
    ):
        client.login(lucy)

        activities = await ActivityService(session, lucy.id).update_create(
            empty_applet_lucy_manager.id,
            [
                ActivityUpdate(
                    **activity_create_session.dict(exclude={"name", "auto_assign"}),
                    name="Hybrid Activity",
                    auto_assign=True,
                )
            ],
        )
        manual_activity = next((activity for activity in activities if activity.name == "Hybrid Activity"))

        await ActivityAssignmentService(session).create_many(
            empty_applet_lucy_manager.id,
            [
                ActivityAssignmentCreate(
                    activity_id=manual_activity.id,
                    respondent_subject_id=user_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                )
            ],
        )

        flows = await FlowService(session).update_create(
            empty_applet_lucy_manager.id,
            [
                FlowUpdate(
                    name="Hybrid Flow",
                    description={Language.ENGLISH: "Hybrid Flow"},
                    auto_assign=True,
                    items=[ActivityFlowItemUpdate(activity_key=manual_activity.key)],
                )
            ],
            {manual_activity.key: manual_activity.id},
        )

        manual_flow = next((flow for flow in flows if flow.name == "Hybrid Flow"))

        await ActivityAssignmentService(session).create_many(
            empty_applet_lucy_manager.id,
            [
                ActivityAssignmentCreate(
                    activity_flow_id=manual_flow.id,
                    respondent_subject_id=user_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                )
            ],
        )

        response = await client.get(
            self.subject_assigned_activities_url.format(
                applet_id=empty_applet_lucy_manager.id, subject_id=user_empty_applet_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]

        assert len(result["activityFlows"]) == 1
        assert len(result["activities"]) == 1

        activity_result = result["activities"][0]

        assert activity_result["id"] == str(manual_activity.id)
        assert activity_result["name"] == manual_activity.name
        assert activity_result["description"] == manual_activity.description[Language.ENGLISH]
        assert activity_result["autoAssign"] is True
        assert len(activity_result["items"]) == 1
        assert len(activity_result["assignments"]) == 1

        activity_assignment = activity_result["assignments"][0]
        assert activity_assignment["activityId"] == str(manual_activity.id)
        assert activity_assignment["respondentSubject"]["id"] == str(user_empty_applet_subject.id)
        assert activity_assignment["targetSubject"]["id"] == str(user_empty_applet_subject.id)

        flow_result = result["activityFlows"][0]

        assert flow_result["id"] == str(manual_flow.id)
        assert flow_result["name"] == manual_flow.name
        assert flow_result["description"] == manual_flow.description[Language.ENGLISH]
        assert flow_result["autoAssign"] is True
        assert len(flow_result["assignments"]) == 1
        assert flow_result["activityIds"][0] == str(manual_flow.items[0].activity_id)

        flow_assignment = flow_result["assignments"][0]
        assert flow_assignment["activityFlowId"] == str(manual_flow.id)
        assert flow_assignment["respondentSubject"]["id"] == str(user_empty_applet_subject.id)
        assert flow_assignment["targetSubject"]["id"] == str(user_empty_applet_subject.id)

    async def test_target_assigned_activities_editor(
        self, client, applet_one_lucy_editor, lucy, lucy_applet_one_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.target_assigned_activities_url.format(
                applet_id=applet_one_lucy_editor.id, subject_id=lucy_applet_one_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result = response.json()["result"]

        assert result[0]["type"] == "ACCESS_DENIED"
        assert result[0]["message"] == "Access denied."

    async def test_target_assigned_activities_incorrect_reviewer(
        self, client, applet_one_lucy_reviewer, lucy, lucy_applet_one_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.target_assigned_activities_url.format(
                applet_id=applet_one_lucy_reviewer.id, subject_id=lucy_applet_one_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result = response.json()["result"]

        assert result[0]["type"] == "ACCESS_DENIED"
        assert result[0]["message"] == "Access denied."

    async def test_target_assigned_activities_participant(
        self, client, applet_one_lucy_respondent, lucy, lucy_applet_one_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.target_assigned_activities_url.format(
                applet_id=applet_one_lucy_respondent.id, subject_id=lucy_applet_one_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result = response.json()["result"]

        assert result[0]["type"] == "ACCESS_DENIED"
        assert result[0]["message"] == "Access denied."

    async def test_target_assigned_activities_participant_other(
        self, client, applet_one_lucy_respondent, lucy, applet_one_user_respondent, user_applet_one_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.target_assigned_activities_url.format(
                applet_id=applet_one_lucy_respondent.id, subject_id=user_applet_one_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.FORBIDDEN
        result = response.json()["result"]

        assert result[0]["type"] == "ACCESS_DENIED"
        assert result[0]["message"] == "Access denied."

    async def test_target_assigned_activities_invalid_applet(
        self, client, applet_one_lucy_manager, lucy, lucy_applet_one_subject
    ):
        client.login(lucy)

        applet_id = uuid.uuid4()

        response = await client.get(
            self.target_assigned_activities_url.format(applet_id=applet_id, subject_id=lucy_applet_one_subject.id)
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND
        result = response.json()["result"]

        assert result[0]["type"] == "NOT_FOUND"
        assert result[0]["message"] == f"No such applets with id={applet_id}."

    async def test_target_assigned_activities_invalid_subject(
        self, client, applet_one_lucy_manager, lucy, lucy_applet_one_subject
    ):
        client.login(lucy)

        subject_id = uuid.uuid4()

        response = await client.get(
            self.target_assigned_activities_url.format(applet_id=applet_one_lucy_manager.id, subject_id=subject_id)
        )

        assert response.status_code == http.HTTPStatus.NOT_FOUND
        result = response.json()["result"]

        assert result[0]["type"] == "NOT_FOUND"
        assert result[0]["message"] == f"Subject with id {subject_id} not found"

    async def test_target_assigned_activities_empty_applet(
        self, client, empty_applet_lucy_manager, lucy, lucy_empty_applet_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.target_assigned_activities_url.format(
                applet_id=empty_applet_lucy_manager.id, subject_id=lucy_empty_applet_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]

        assert result == []

    async def test_target_assigned_activities_auto_assigned(
        self, client, applet_activity_flow_lucy_manager, lucy, lucy_applet_activity_flow_subject
    ):
        client.login(lucy)

        response = await client.get(
            self.target_assigned_activities_url.format(
                applet_id=applet_activity_flow_lucy_manager.id, subject_id=lucy_applet_activity_flow_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]

        assert len(result) == 2

        flow = applet_activity_flow_lucy_manager.activity_flows[0]
        flow_result = result[0]

        assert flow_result["id"] == str(flow.id)
        assert flow_result["name"] == flow.name
        assert flow_result["description"] == flow.description[Language.ENGLISH]
        assert flow_result["isFlow"] is True
        assert flow_result["autoAssign"] == flow.auto_assign
        assert flow_result["status"] == ActivityOrFlowStatusEnum.ACTIVE.value
        assert len(flow_result["activityIds"]) == 1
        assert flow_result["activityIds"][0] == str(flow.items[0].activity_id)
        assert len(flow_result["assignments"]) == 0

        activity = applet_activity_flow_lucy_manager.activities[0]
        activity_result = result[1]

        assert activity_result["id"] == str(activity.id)
        assert activity_result["name"] == activity.name
        assert activity_result["description"] == activity.description[Language.ENGLISH]
        assert activity_result["isFlow"] is False
        assert activity_result["autoAssign"] == activity.auto_assign
        assert activity_result["status"] == ActivityOrFlowStatusEnum.ACTIVE.value
        assert activity_result["activityIds"] is None
        assert len(activity_result["assignments"]) == 0

    async def test_target_assigned_activities_manually_assigned(
        self,
        session,
        client,
        empty_applet_lucy_manager,
        lucy,
        lucy_empty_applet_subject,
        user_empty_applet_subject,
        activity_create_session: ActivityCreate,
    ):
        client.login(lucy)

        activities = await ActivityService(session, lucy.id).update_create(
            empty_applet_lucy_manager.id,
            [
                ActivityUpdate(
                    **activity_create_session.dict(exclude={"name", "auto_assign"}),
                    name="Manual Activity 1",
                    auto_assign=False,
                ),
                ActivityUpdate(
                    **activity_create_session.dict(exclude={"name", "auto_assign"}),
                    name="Manual Activity 2",
                    auto_assign=False,
                ),
                ActivityUpdate(
                    **activity_create_session.dict(exclude={"name", "auto_assign"}),
                    name="Manual Activity 3",
                    auto_assign=False,
                ),
                ActivityUpdate(
                    **activity_create_session.dict(exclude={"name", "auto_assign"}),
                    name="Manual Activity 4",
                    auto_assign=False,
                ),
            ],
        )
        manual_activity_1 = next((activity for activity in activities if activity.name == "Manual Activity 1"))
        manual_activity_2 = next((activity for activity in activities if activity.name == "Manual Activity 2"))
        manual_activity_3 = next((activity for activity in activities if activity.name == "Manual Activity 3"))
        manual_activity_4 = next((activity for activity in activities if activity.name == "Manual Activity 4"))

        await ActivityAssignmentService(session).create_many(
            empty_applet_lucy_manager.id,
            [
                ActivityAssignmentCreate(
                    activity_id=manual_activity_1.id,
                    activity_flow_id=None,
                    respondent_subject_id=user_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=manual_activity_2.id,
                    activity_flow_id=None,
                    respondent_subject_id=user_empty_applet_subject.id,
                    target_subject_id=lucy_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=manual_activity_3.id,
                    activity_flow_id=None,
                    respondent_subject_id=lucy_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=manual_activity_4.id,
                    activity_flow_id=None,
                    respondent_subject_id=lucy_empty_applet_subject.id,
                    target_subject_id=lucy_empty_applet_subject.id,
                ),
            ],
        )

        flows = await FlowService(session).update_create(
            empty_applet_lucy_manager.id,
            [
                FlowUpdate(
                    name="Manual Flow 1",
                    description={Language.ENGLISH: "Manual Flow"},
                    auto_assign=False,
                    items=[ActivityFlowItemUpdate(activity_key=manual_activity_1.key)],
                ),
                FlowUpdate(
                    name="Manual Flow 2",
                    description={Language.ENGLISH: "Manual Flow"},
                    auto_assign=False,
                    items=[ActivityFlowItemUpdate(activity_key=manual_activity_2.key)],
                ),
                FlowUpdate(
                    name="Manual Flow 3",
                    description={Language.ENGLISH: "Manual Flow"},
                    auto_assign=False,
                    items=[ActivityFlowItemUpdate(activity_key=manual_activity_3.key)],
                ),
                FlowUpdate(
                    name="Manual Flow 4",
                    description={Language.ENGLISH: "Manual Flow"},
                    auto_assign=False,
                    items=[ActivityFlowItemUpdate(activity_key=manual_activity_4.key)],
                ),
            ],
            {
                manual_activity_1.key: manual_activity_1.id,
                manual_activity_2.key: manual_activity_2.id,
                manual_activity_3.key: manual_activity_3.id,
                manual_activity_4.key: manual_activity_4.id,
            },
        )

        manual_flow_1 = next((flow for flow in flows if flow.name == "Manual Flow 1"))
        manual_flow_2 = next((flow for flow in flows if flow.name == "Manual Flow 2"))
        manual_flow_3 = next((flow for flow in flows if flow.name == "Manual Flow 3"))
        manual_flow_4 = next((flow for flow in flows if flow.name == "Manual Flow 4"))

        await ActivityAssignmentService(session).create_many(
            empty_applet_lucy_manager.id,
            [
                ActivityAssignmentCreate(
                    activity_id=None,
                    activity_flow_id=manual_flow_1.id,
                    respondent_subject_id=user_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=None,
                    activity_flow_id=manual_flow_2.id,
                    respondent_subject_id=user_empty_applet_subject.id,
                    target_subject_id=lucy_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=None,
                    activity_flow_id=manual_flow_3.id,
                    respondent_subject_id=lucy_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                ),
                ActivityAssignmentCreate(
                    activity_id=None,
                    activity_flow_id=manual_flow_4.id,
                    respondent_subject_id=lucy_empty_applet_subject.id,
                    target_subject_id=lucy_empty_applet_subject.id,
                ),
            ],
        )

        response = await client.get(
            self.target_assigned_activities_url.format(
                applet_id=empty_applet_lucy_manager.id, subject_id=user_empty_applet_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]

        assert len(result) == 4

        flow_result_1 = next(
            (flow_result for flow_result in [result[0], result[1]] if flow_result["id"] == str(manual_flow_1.id))
        )
        assert flow_result_1["id"] == str(manual_flow_1.id)
        assert flow_result_1["name"] == manual_flow_1.name
        assert flow_result_1["description"] == manual_flow_1.description[Language.ENGLISH]
        assert flow_result_1["isFlow"] is True
        assert flow_result_1["status"] == ActivityOrFlowStatusEnum.ACTIVE.value
        assert flow_result_1["autoAssign"] is False
        assert len(flow_result_1["assignments"]) == 1
        assert flow_result_1["activityIds"][0] == str(manual_flow_1.items[0].activity_id)

        flow_assignment_1 = flow_result_1["assignments"][0]
        assert flow_assignment_1["activityFlowId"] == str(manual_flow_1.id)
        assert flow_assignment_1["targetSubject"]["id"] == str(user_empty_applet_subject.id)

        flow_result_2 = next(
            (flow_result for flow_result in [result[0], result[1]] if flow_result["id"] == str(manual_flow_3.id))
        )
        assert flow_result_2["id"] == str(manual_flow_3.id)
        assert flow_result_2["name"] == manual_flow_3.name
        assert flow_result_2["description"] == manual_flow_3.description[Language.ENGLISH]
        assert flow_result_2["isFlow"] is True
        assert flow_result_2["status"] == ActivityOrFlowStatusEnum.ACTIVE.value
        assert flow_result_2["autoAssign"] is False
        assert len(flow_result_2["assignments"]) == 1
        assert flow_result_2["activityIds"][0] == str(manual_flow_3.items[0].activity_id)

        flow_assignment_2 = flow_result_2["assignments"][0]
        assert flow_assignment_2["activityFlowId"] == str(manual_flow_3.id)
        assert flow_assignment_2["targetSubject"]["id"] == str(user_empty_applet_subject.id)

        activity_result_1 = next(
            (
                activity_result
                for activity_result in [result[2], result[3]]
                if activity_result["id"] == str(manual_activity_1.id)
            )
        )
        assert activity_result_1["id"] == str(manual_activity_1.id)
        assert activity_result_1["name"] == manual_activity_1.name
        assert activity_result_1["description"] == manual_activity_1.description[Language.ENGLISH]
        assert activity_result_1["isFlow"] is False
        assert activity_result_1["status"] == ActivityOrFlowStatusEnum.ACTIVE.value
        assert activity_result_1["autoAssign"] is False
        assert len(activity_result_1["assignments"]) == 1
        assert activity_result_1["activityIds"] is None

        activity_assignment = activity_result_1["assignments"][0]
        assert activity_assignment["activityId"] == str(manual_activity_1.id)
        assert activity_assignment["targetSubject"]["id"] == str(user_empty_applet_subject.id)

        activity_result_2 = next(
            (
                activity_result
                for activity_result in [result[2], result[3]]
                if activity_result["id"] == str(manual_activity_3.id)
            )
        )
        assert activity_result_2["id"] == str(manual_activity_3.id)
        assert activity_result_2["name"] == manual_activity_3.name
        assert activity_result_2["description"] == manual_activity_3.description[Language.ENGLISH]
        assert activity_result_2["isFlow"] is False
        assert activity_result_2["status"] == ActivityOrFlowStatusEnum.ACTIVE.value
        assert activity_result_2["autoAssign"] is False
        assert len(activity_result_2["assignments"]) == 1
        assert activity_result_2["activityIds"] is None

        activity_assignment = activity_result_2["assignments"][0]
        assert activity_assignment["activityId"] == str(manual_activity_3.id)
        assert activity_assignment["targetSubject"]["id"] == str(user_empty_applet_subject.id)

    async def test_target_assigned_activity_from_submission(
        self,
        session,
        client,
        tom: User,
        tom_applet_one_subject: Subject,
        lucy_applet_one_subject: Subject,
        applet_one_lucy_respondent: AppletFull,
        answer_create_payload: dict,
    ):
        activity = applet_one_lucy_respondent.activities[0]

        activity_service = ActivityService(session, tom.id)
        await activity_service.remove_applet_activities(applet_one_lucy_respondent.id)
        await activity_service.update_create(
            applet_one_lucy_respondent.id,
            [
                ActivityUpdate(
                    **activity.dict(exclude={"auto_assign"}),
                    auto_assign=False,
                ),
            ],
        )

        # Create an activity answer
        await AnswerService(session, tom.id).create_answer(
            AppletAnswerCreate(
                **answer_create_payload,
                input_subject_id=lucy_applet_one_subject.id,
                source_subject_id=lucy_applet_one_subject.id,
                target_subject_id=tom_applet_one_subject.id,
            )
        )

        client.login(tom)

        response = await client.get(
            self.target_assigned_activities_url.format(
                applet_id=applet_one_lucy_respondent.id, subject_id=tom_applet_one_subject.id
            )
        )
        assert response.status_code == http.HTTPStatus.OK

        result = response.json()["result"]
        assert len(result) == 1

        activity_result = result[0]
        assert activity_result["id"] == str(activity.id)
        assert activity_result["name"] == activity.name
        assert activity_result["description"] == activity.description[Language.ENGLISH]
        assert activity_result["status"] == ActivityOrFlowStatusEnum.INACTIVE.value
        assert activity_result["isFlow"] is False
        assert activity_result["autoAssign"] is False
        assert activity_result["activityIds"] is None
        assert len(activity_result["assignments"]) == 0

    async def test_target_assigned_hidden_activity(
        self,
        session,
        client,
        empty_applet_lucy_manager,
        lucy,
        lucy_empty_applet_subject,
        user_empty_applet_subject,
        activity_create_session: ActivityCreate,
    ):
        client.login(lucy)

        activities = await ActivityService(session, lucy.id).update_create(
            empty_applet_lucy_manager.id,
            [
                ActivityUpdate(
                    **activity_create_session.dict(exclude={"name", "auto_assign", "is_hidden"}),
                    name="Auto Activity",
                    auto_assign=True,
                    is_hidden=True,
                ),
                ActivityUpdate(
                    **activity_create_session.dict(exclude={"name", "auto_assign", "is_hidden"}),
                    name="Manual Activity",
                    auto_assign=False,
                    is_hidden=True,
                ),
            ],
        )
        auto_activity = next((activity for activity in activities if activity.name == "Auto Activity"))
        manual_activity = next((activity for activity in activities if activity.name == "Manual Activity"))

        await ActivityAssignmentService(session).create_many(
            empty_applet_lucy_manager.id,
            [
                ActivityAssignmentCreate(
                    activity_id=manual_activity.id,
                    activity_flow_id=None,
                    respondent_subject_id=lucy_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                ),
            ],
        )

        flows = await FlowService(session).update_create(
            empty_applet_lucy_manager.id,
            [
                FlowUpdate(
                    name="Auto Flow",
                    description={Language.ENGLISH: "Auto Flow"},
                    auto_assign=True,
                    items=[ActivityFlowItemUpdate(activity_key=auto_activity.key)],
                    is_hidden=True,
                ),
                FlowUpdate(
                    name="Manual Flow",
                    description={Language.ENGLISH: "Manual Flow"},
                    auto_assign=False,
                    items=[ActivityFlowItemUpdate(activity_key=manual_activity.key)],
                    is_hidden=True,
                ),
            ],
            {
                auto_activity.key: auto_activity.id,
                manual_activity.key: manual_activity.id,
            },
        )

        auto_flow = next((flow for flow in flows if flow.name == "Auto Flow"))
        manual_flow = next((flow for flow in flows if flow.name == "Manual Flow"))

        await ActivityAssignmentService(session).create_many(
            empty_applet_lucy_manager.id,
            [
                ActivityAssignmentCreate(
                    activity_id=None,
                    activity_flow_id=manual_flow.id,
                    respondent_subject_id=lucy_empty_applet_subject.id,
                    target_subject_id=user_empty_applet_subject.id,
                ),
            ],
        )

        response = await client.get(
            self.target_assigned_activities_url.format(
                applet_id=empty_applet_lucy_manager.id, subject_id=user_empty_applet_subject.id
            )
        )

        assert response.status_code == http.HTTPStatus.OK
        result = response.json()["result"]

        assert len(result) == 4

        flow_result_1 = result[0]
        flow_result_2 = result[1]

        manual_flow_result = flow_result_1 if not flow_result_1["autoAssign"] else flow_result_2
        assert manual_flow_result["id"] == str(manual_flow.id)
        assert manual_flow_result["name"] == manual_flow.name
        assert manual_flow_result["description"] == manual_flow.description[Language.ENGLISH]
        assert manual_flow_result["isFlow"] is True
        assert manual_flow_result["status"] == ActivityOrFlowStatusEnum.HIDDEN.value
        assert manual_flow_result["autoAssign"] is False
        assert len(manual_flow_result["assignments"]) == 1
        assert manual_flow_result["activityIds"][0] == str(manual_flow.items[0].activity_id)

        flow_assignment = manual_flow_result["assignments"][0]
        assert flow_assignment["activityFlowId"] == str(manual_flow.id)
        assert flow_assignment["targetSubject"]["id"] == str(user_empty_applet_subject.id)

        auto_flow_result = flow_result_1 if flow_result_1["autoAssign"] else flow_result_2
        assert auto_flow_result["id"] == str(auto_flow.id)
        assert auto_flow_result["name"] == auto_flow.name
        assert auto_flow_result["description"] == auto_flow.description[Language.ENGLISH]
        assert auto_flow_result["isFlow"] is True
        assert auto_flow_result["status"] == ActivityOrFlowStatusEnum.HIDDEN.value
        assert auto_flow_result["autoAssign"] is True
        assert len(auto_flow_result["assignments"]) == 0
        assert auto_flow_result["activityIds"][0] == str(auto_flow.items[0].activity_id)

        activity_result_1 = result[2]
        activity_result_2 = result[3]

        manual_activity_result = activity_result_1 if not activity_result_1["autoAssign"] else activity_result_2
        assert manual_activity_result["id"] == str(manual_activity.id)
        assert manual_activity_result["name"] == manual_activity.name
        assert manual_activity_result["description"] == manual_activity.description[Language.ENGLISH]
        assert manual_activity_result["isFlow"] is False
        assert manual_activity_result["status"] == ActivityOrFlowStatusEnum.HIDDEN.value
        assert manual_activity_result["autoAssign"] is False
        assert len(manual_activity_result["assignments"]) == 1
        assert manual_activity_result["activityIds"] is None

        activity_assignment = manual_activity_result["assignments"][0]
        assert activity_assignment["activityId"] == str(manual_activity.id)
        assert activity_assignment["targetSubject"]["id"] == str(user_empty_applet_subject.id)

        auto_activity_result = activity_result_1 if activity_result_1["autoAssign"] else activity_result_2
        assert auto_activity_result["id"] == str(auto_activity.id)
        assert auto_activity_result["name"] == auto_activity.name
        assert auto_activity_result["description"] == auto_activity.description[Language.ENGLISH]
        assert auto_activity_result["isFlow"] is False
        assert auto_activity_result["status"] == ActivityOrFlowStatusEnum.HIDDEN.value
        assert auto_activity_result["autoAssign"] is True
        assert len(auto_activity_result["assignments"]) == 0
        assert auto_activity_result["activityIds"] is None
