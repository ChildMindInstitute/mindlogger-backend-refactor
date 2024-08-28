import copy
import http
import uuid
from typing import cast

import pytest
from pydantic.color import Color
from pytest import FixtureRequest

from apps.activities import errors as activity_errors
from apps.activities.domain.activity_create import ActivityCreate, ActivityItemCreate
from apps.activities.domain.conditional_logic import ConditionalLogic, Match
from apps.activities.domain.conditions import EqualToOptionCondition, OptionPayload, SingleSelectConditionType
from apps.activities.domain.response_type_config import PerformanceTaskType, ResponseType, SingleSelectionConfig
from apps.activities.domain.response_values import SingleSelectionValues, SliderValues
from apps.activities.domain.scores_reports import (
    ScoreConditionalLogic,
    ScoresAndReports,
    SectionConditionalLogic,
    Subscale,
    SubScaleLookupTable,
    SubscaleSetting,
    TotalScoreTable,
)
from apps.applets.domain.applet_create_update import AppletCreate, AppletUpdate
from apps.applets.domain.applet_full import AppletFull
from apps.shared.enums import Language
from apps.shared.test.client import TestClient
from apps.users.domain import User


@pytest.fixture
def activity_create_with_conditional_logic(
    activity_create_session: ActivityCreate,
    single_select_item_create: ActivityItemCreate,
) -> ActivityCreate:
    activity = activity_create_session.copy(deep=True)
    single_select_item_create.response_values = cast(SingleSelectionValues, single_select_item_create.response_values)
    single_select_with_cond = single_select_item_create.copy(deep=True)
    single_select_with_cond.name = single_select_item_create.name + "_with_conditional_logic"
    single_select_with_cond.conditional_logic = ConditionalLogic(
        match=Match.ALL,
        conditions=[
            EqualToOptionCondition(
                item_name=single_select_item_create.name,
                type=SingleSelectConditionType.EQUAL_TO_OPTION,
                payload=OptionPayload(option_value=str(single_select_item_create.response_values.options[0].value)),
            ),
        ],
    )
    activity.items = [single_select_item_create, single_select_with_cond]
    return activity


@pytest.fixture
def single_select_item_create_with_score(single_select_item_create: ActivityItemCreate) -> ActivityItemCreate:
    item_create = single_select_item_create.copy(deep=True)
    item_create.config = cast(SingleSelectionConfig, item_create.config)
    item_create.response_values = cast(SingleSelectionValues, item_create.response_values)
    item_create.response_values.options[0].score = 1
    item_create.config.add_scores = True
    return item_create


class TestActivityItems:
    login_url = "/auth/login"
    applet_list_url = "applets"
    applet_create_url = "workspaces/{owner_id}/applets"
    applet_detail_url = f"{applet_list_url}/{{pk}}"
    activity_detail_url = "activities/{activity_id}"
    applet_workspace_detail_url = "workspaces/{owner_id}/applets/{pk}"

    @pytest.mark.parametrize(
        "item_fixture",
        (
            "single_select_item_create",
            "multi_select_item_create",
            "slider_item_create",
            "date_item_create",
            "number_selection_item_create",
            "time_item_create",
            "time_range_item_create",
            "single_select_row_item_create",
            "multi_select_row_item_create",
            "slider_rows_item_create",
            "text_item_create",
            "drawing_item_create",
            "photo_item_create",
            "video_item_create",
            "geolocation_item_create",
            "audio_item_create",
            "message_item_create",
            "audio_player_item_create",
            "paragraph_text_item_create",
        ),
    )
    async def test_create_applet_with_each_activity_item(
        self,
        client: TestClient,
        tom: User,
        applet_minimal_data: AppletCreate,
        item_fixture: str,
        request: FixtureRequest,
    ):
        client.login(tom)
        item_create = request.getfixturevalue(item_fixture)
        data = applet_minimal_data.copy(deep=True)
        data.activities[0].items = [item_create]
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        resp = await client.get(
            self.applet_workspace_detail_url.format(owner_id=tom.id, pk=resp.json()["result"]["id"])
        )
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        items = result["activities"][0]["items"]
        assert len(items) == 1
        item = items[0]
        assert item["responseType"] == item_create.response_type
        assert item["name"] == item_create.name
        assert item["question"] == item_create.question
        assert item["isHidden"] == item_create.is_hidden
        assert not item["allowEdit"]
        if item_create.response_type in ResponseType.get_non_response_types():
            assert item["responseValues"] is None
        else:
            assert item["responseValues"] == item_create.response_values.dict(by_alias=True)

    @pytest.mark.parametrize(
        "item_fixture", ("phrasal_template_with_text_create", "phrasal_template_with_slider_rows_create")
    )
    async def test_create_applet_with_phrasal_template(
        self,
        client: TestClient,
        tom: User,
        applet_minimal_data: AppletCreate,
        item_fixture: str,
        request: FixtureRequest,
    ):
        client.login(tom)
        items_create = request.getfixturevalue(item_fixture)
        data = applet_minimal_data.copy(deep=True)
        data.activities[0].items = items_create
        phrasal_item = next(
            item for item in data.activities[0].items if item.response_type == ResponseType.PHRASAL_TEMPLATE
        )
        assert phrasal_item
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        resp = await client.get(
            self.applet_workspace_detail_url.format(owner_id=tom.id, pk=resp.json()["result"]["id"])
        )
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        items = result["activities"][0]["items"]
        assert len(items) == 2
        item = next(item for item in items if item["responseType"] == phrasal_item.response_type)
        assert item["responseType"] == phrasal_item.response_type
        assert item["name"] == phrasal_item.name
        assert item["question"] == phrasal_item.question
        assert item["isHidden"] == phrasal_item.is_hidden
        assert not item["allowEdit"]
        assert item["responseValues"] == phrasal_item.response_values.dict(by_alias=True)  # type: ignore

    @pytest.mark.parametrize(
        "fixture_name, performance_task_type",
        (
            ("activity_ab_trails_ipad_create", PerformanceTaskType.ABTRAILS),
            ("activity_ab_trails_mobile_create", PerformanceTaskType.ABTRAILS),
            ("activity_flanker_create", PerformanceTaskType.FLANKER),
            ("actvitiy_cst_gyroscope_create", PerformanceTaskType.GYROSCOPE),
            ("actvitiy_cst_touch_create", PerformanceTaskType.TOUCH),
            ("actvitiy_unity_create", PerformanceTaskType.UNITY),
        ),
    )
    async def test_create_applet_with_performance_task(
        self,
        client: TestClient,
        tom: User,
        applet_minimal_data: AppletCreate,
        request: FixtureRequest,
        fixture_name: str,
        performance_task_type: PerformanceTaskType,
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        activity = request.getfixturevalue(fixture_name)
        data.activities = [activity]
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        activities = resp.json()["result"]["activities"]
        assert len(activities) == 1
        assert activities[0]["isPerformanceTask"]
        assert activities[0]["performanceTaskType"] == performance_task_type
        # Check that the 'get' after creating new applet returns correct performance task type
        resp = await client.get(
            self.applet_workspace_detail_url.format(
                owner_id=tom.id,
                pk=resp.json()["result"]["id"],
            )
        )
        assert resp.status_code == http.HTTPStatus.OK
        assert resp.json()["result"]["activities"][0]["isPerformanceTask"]
        assert resp.json()["result"]["activities"][0]["performanceTaskType"] == performance_task_type

    async def test_creating_applet_with_activity_items_condition(
        self,
        client: TestClient,
        tom: User,
        applet_minimal_data: AppletCreate,
        activity_create_with_conditional_logic: ActivityCreate,
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        data.activities = [activity_create_with_conditional_logic]
        response = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert response.status_code == http.HTTPStatus.CREATED

        activity_id = response.json()["result"]["activities"][0]["id"]
        response = await client.get(self.activity_detail_url.format(activity_id=activity_id))
        assert response.status_code == http.HTTPStatus.OK
        assert isinstance(response.json()["result"]["items"][1]["conditionalLogic"], dict)

    async def test_creating_applet_with_activity_items_condition_not_valid_order_in_conditional_logic(
        self,
        client: TestClient,
        tom: User,
        applet_minimal_data: AppletCreate,
        activity_create_with_conditional_logic: ActivityCreate,
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        data.activities = [activity_create_with_conditional_logic]
        item_for_condition = activity_create_with_conditional_logic.items[0]
        item_with_condition = activity_create_with_conditional_logic.items[1]
        # Make wrong order. Item with condition must be after item which value is included in conditional logic
        request_data = data.dict()
        request_data["activities"][0]["items"] = [item_with_condition.dict(), item_for_condition.dict()]
        response = await client.post(self.applet_create_url.format(owner_id=tom.id), data=request_data)
        assert response.status_code == http.HTTPStatus.BAD_REQUEST
        result = response.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == activity_errors.IncorrectConditionItemIndexError.message

    async def test_create_applet__activity_with_conditional_logic(
        self,
        client: TestClient,
        tom: User,
        applet_minimal_data: AppletCreate,
        activity_create_with_conditional_logic: ActivityCreate,
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        data.activities = [activity_create_with_conditional_logic]
        response = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert response.status_code == http.HTTPStatus.CREATED
        result = response.json()["result"]
        item_create_with_logic = activity_create_with_conditional_logic.items[1]
        assert item_create_with_logic.conditional_logic is not None
        assert result["activities"][0]["items"][1]["conditionalLogic"] == item_create_with_logic.conditional_logic.dict(
            by_alias=True
        )

    @pytest.mark.parametrize(
        "item_fixture_name",
        (
            "single_select_item_create",
            "multi_select_item_create",
            "single_select_row_item_create",
            "multi_select_row_item_create",
        ),
    )
    async def test_creating_activity_items_without_option_value(
        self,
        client: TestClient,
        tom: User,
        item_fixture_name: str,
        request: FixtureRequest,
        applet_minimal_data: AppletCreate,
    ):
        client.login(tom)
        item = request.getfixturevalue(item_fixture_name)
        data = applet_minimal_data.copy(deep=True)
        # row
        if hasattr(item.response_values, "data_matrix"):
            item.response_values.data_matrix[0].options[0].value = None
        else:
            item.response_values.options[0].value = None
        data.activities[0].items = [item]
        response = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert response.status_code == http.HTTPStatus.CREATED
        response_values = response.json()["result"]["activities"][0]["items"][0]["responseValues"]
        if "dataMatrix" in response_values:
            assert response_values["dataMatrix"][0]["options"][0]["value"] == 0
        else:
            assert response_values["options"][0]["value"] == 0

    @pytest.mark.parametrize("response_type", (ResponseType.SINGLESELECT, ResponseType.MULTISELECT))
    async def test_create_applet_single_multi_select_response_values_value_null_auto_set_value(
        self, client, applet_minimal_data, tom, response_type
    ) -> None:
        client.login(tom)
        data = applet_minimal_data.copy(deep=True).dict()
        item = data["activities"][0]["items"][0]
        option = item["response_values"]["options"][0]
        del option["value"]
        option2 = copy.deepcopy(option)
        option2["value"] = None
        item["response_values"]["options"].append(option2)
        item["response_type"] = response_type
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == http.HTTPStatus.CREATED
        item = resp.json()["result"]["activities"][0]["items"][0]
        # We can use enumerate because we have 2 options and values should be
        # 0 and 1
        for i, o in enumerate(item["responseValues"]["options"]):
            assert o["value"] == i

    async def test_create_applet_flow_wrong_activity_key(
        self, client: TestClient, applet_minimal_data: AppletCreate, tom: User
    ) -> None:
        client.login(tom)
        data = applet_minimal_data.dict()
        activity_key = data["activities"][0]["key"]
        activity_wrong_key = uuid.uuid4()
        data["activity_flows"].append(
            dict(
                name="Morning questionnaire",
                description=dict(
                    en="Understand how was the morning",
                    fr="Understand how was the morning",
                ),
                items=[dict(activity_key=activity_wrong_key)],
            )
        )
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == activity_errors.FlowItemActivityKeyNotFoundError.status_code
        assert resp.json()["result"][0]["message"] == activity_errors.FlowItemActivityKeyNotFoundError.message

        data["activity_flows"][0]["items"][0]["activity_key"] = activity_key
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == http.HTTPStatus.CREATED

    async def test_update_applet_duplicated_activity_item_name_is_not_allowed(
        self, client: TestClient, applet_minimal_data: AppletCreate, tom: User, applet_one: AppletFull
    ):
        client.login(tom)
        data = AppletUpdate(**applet_minimal_data.dict(exclude_unset=True)).dict()
        item = copy.deepcopy(data["activities"][0]["items"][0])
        data["activities"][0]["items"].append(item)
        resp = await client.put(
            self.applet_detail_url.format(pk=applet_one.id),
            data=data,
        )
        assert resp.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == activity_errors.DuplicateActivityItemNameNameError.message

    @pytest.mark.parametrize(
        "fixture_name",
        ("single_select_item_create", "multi_select_item_create"),
    )
    async def test_create_applet__item_single_multi_select_with_image(
        self,
        client: TestClient,
        applet_minimal_data: AppletCreate,
        tom: User,
        fixture_name: str,
        remote_image: str,
        request: FixtureRequest,
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        item_create = request.getfixturevalue(fixture_name)
        item_create.response_values.options[0].image = remote_image
        data.activities[0].items = [item_create]
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        assert (
            resp.json()["result"]["activities"][0]["items"][0]["responseValues"]["options"][0]["image"] == remote_image
        )

    @pytest.mark.parametrize(
        "fixture_name",
        ("single_select_item_create", "multi_select_item_create"),
    )
    async def test_create_applet__item_single_multi_select_with_color(
        self,
        client: TestClient,
        applet_minimal_data: AppletCreate,
        tom: User,
        fixture_name: str,
        request: FixtureRequest,
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        item_create = request.getfixturevalue(fixture_name)
        color = Color("#ffffff")
        item_create.response_values.options[0].color = color
        data.activities[0].items = [item_create]
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        assert (
            resp.json()["result"]["activities"][0]["items"][0]["responseValues"]["options"][0]["color"]
            == color.as_hex()
        )

    async def test_create_applet__item_slider_with_color(
        self,
        client: TestClient,
        applet_minimal_data: AppletCreate,
        tom: User,
        remote_image: str,
        slider_item_create: ActivityItemCreate,
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        slider_item_create.response_values = cast(SliderValues, slider_item_create.response_values)
        slider_item_create.response_values.min_image = remote_image
        slider_item_create.response_values.max_image = remote_image
        data.activities[0].items = [slider_item_create]
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        assert resp.json()["result"]["activities"][0]["items"][0]["responseValues"]["minImage"] == remote_image
        assert resp.json()["result"]["activities"][0]["items"][0]["responseValues"]["maxImage"] == remote_image

    async def test_create_applet__activity_with_subscale_settings__subscale_type_item(
        self,
        client: TestClient,
        applet_minimal_data: AppletCreate,
        tom: User,
        subscale_setting: SubscaleSetting,
        single_select_item_create_with_score: ActivityItemCreate,
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        sub_setting = subscale_setting.copy(deep=True)
        # subscale item must have name from activity. So for test just update name in copied subscale item
        sub_setting.subscales[0].items[0].name = single_select_item_create_with_score.name  # type: ignore[index]
        data.activities[0].items = [single_select_item_create_with_score]
        data.activities[0].subscale_setting = sub_setting
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        result = resp.json()["result"]
        assert result["activities"][0]["subscaleSetting"] == sub_setting.dict(by_alias=True)

    async def test_create_applet__activity_with_subscale_settings__subscale_type_subscale(
        self,
        client: TestClient,
        applet_minimal_data: AppletCreate,
        single_select_item_create_with_score: ActivityItemCreate,
        tom: User,
        subscale_setting: SubscaleSetting,
        subscale_with_item_type_subscale: Subscale,
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        sub_settin = subscale_setting.copy(deep=True)
        # subscale item must have name from activity. So for test just update name in copied subscale item
        sub_settin.subscales[0].items[0].name = single_select_item_create_with_score.name  # type: ignore[index]
        # Add subscale type subscale which has subscale item pointing to the subscale above
        sub_settin.subscales.append(subscale_with_item_type_subscale)  # type: ignore[union-attr]
        data.activities[0].items = [single_select_item_create_with_score]
        data.activities[0].subscale_setting = sub_settin
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        result = resp.json()["result"]
        assert result["activities"][0]["subscaleSetting"] == sub_settin.dict(by_alias=True)

    async def test_create_applet__activity_with_subscale_settings_with_total_score_table(
        self,
        client: TestClient,
        applet_minimal_data: AppletCreate,
        single_select_item_create_with_score: ActivityItemCreate,
        tom: User,
        subscale_setting: SubscaleSetting,
        subscale_total_score_table: list[TotalScoreTable],
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        sub_setting = subscale_setting.copy(deep=True)
        # subscale item must have name from activity. So for test just update name in copied subscale item
        sub_setting.subscales[0].items[0].name = single_select_item_create_with_score.name  # type: ignore[index]
        sub_setting.total_scores_table_data = subscale_total_score_table
        data.activities[0].items = [single_select_item_create_with_score]
        data.activities[0].subscale_setting = sub_setting
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        result = resp.json()["result"]
        assert result["activities"][0]["subscaleSetting"] == sub_setting.dict(by_alias=True)

    async def test_create_applet__activity_with_subscale_settings_with_subscale_lookup_table(
        self,
        client: TestClient,
        applet_minimal_data: AppletCreate,
        single_select_item_create_with_score: ActivityItemCreate,
        tom: User,
        subscale_setting: SubscaleSetting,
        subscale_lookup_table: list[SubScaleLookupTable],
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        sub_setting = subscale_setting.copy(deep=True)
        # subscale item must have name from activity. So for test just update name in copied subscale item
        sub_setting.subscales[0].items[0].name = single_select_item_create_with_score.name  # type: ignore[index]
        sub_setting.subscales[0].subscale_table_data = subscale_lookup_table  # type: ignore[index]
        data.activities[0].items = [single_select_item_create_with_score]
        data.activities[0].subscale_setting = sub_setting
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        result = resp.json()["result"]
        assert result["activities"][0]["subscaleSetting"] == sub_setting.dict(by_alias=True)

    async def test_create_applet__activity_with_score_and_reports__score_and_section(
        self,
        client: TestClient,
        applet_minimal_data: AppletCreate,
        tom: User,
        scores_and_reports: ScoresAndReports,
        single_select_item_create_with_score: ActivityItemCreate,
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        reports_data = scores_and_reports.copy(deep=True)
        reports_data.reports[0].items_print = [single_select_item_create_with_score.name]  # type: ignore[index]
        data.activities[0].items = [single_select_item_create_with_score]
        data.activities[0].scores_and_reports = reports_data
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        result = resp.json()["result"]
        assert result["activities"][0]["scoresAndReports"] == reports_data.dict(by_alias=True)

    async def test_create_applet__activity_with_score_and_reports__score_and_section_with_conditional_logic(
        self,
        client: TestClient,
        applet_minimal_data: AppletCreate,
        tom: User,
        scores_and_reports: ScoresAndReports,
        score_conditional_logic: ScoreConditionalLogic,
        section_conditional_logic: SectionConditionalLogic,
        single_select_item_create_with_score: ActivityItemCreate,
    ):
        client.login(tom)
        data = applet_minimal_data.copy(deep=True)
        reports_data = scores_and_reports.copy(deep=True)
        reports_data.reports[0].items_print = [single_select_item_create_with_score.name]  # type: ignore[index]
        reports_data.reports[1].items_print = [single_select_item_create_with_score.name]  # type: ignore[index]
        score_conditional_logic.items_print = [single_select_item_create_with_score.name]
        reports_data.reports[0].conditional_logic = [score_conditional_logic]  # type: ignore[index]
        reports_data.reports[1].conditional_logic = section_conditional_logic  # type: ignore[index]
        data.activities[0].items = [single_select_item_create_with_score]
        data.activities[0].scores_and_reports = reports_data
        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        result = resp.json()["result"]
        assert result["activities"][0]["scoresAndReports"] == reports_data.dict(by_alias=True)

    @pytest.mark.parametrize(
        "item_fixture",
        ("message_item_create",),
    )
    async def test_create_applet_with_activity_sanitize_strings(
        self,
        client: TestClient,
        tom: User,
        applet_minimal_data: AppletCreate,
        item_fixture: str,
        request: FixtureRequest,
    ):
        text_with_script_inside = "One <script>alert('test')</script> Two"
        sanitized_text = "One  Two"
        client.login(tom)
        item_create = request.getfixturevalue(item_fixture)
        item_create.question = {"en": text_with_script_inside}
        data = applet_minimal_data.copy(deep=True)
        data.activities[0].items = [item_create]

        data.display_name = text_with_script_inside
        data.about = {Language.ENGLISH: text_with_script_inside}
        data.description = {Language.ENGLISH: text_with_script_inside}
        data.activities[0].name = text_with_script_inside
        data.activities[0].description = {Language.ENGLISH: text_with_script_inside}

        resp = await client.post(self.applet_create_url.format(owner_id=tom.id), data=data)
        assert resp.status_code == http.HTTPStatus.CREATED
        resp = await client.get(
            self.applet_workspace_detail_url.format(owner_id=tom.id, pk=resp.json()["result"]["id"])
        )
        assert resp.status_code == http.HTTPStatus.OK
        result = resp.json()["result"]
        result["displayName"] = sanitized_text
        result["about"] = sanitized_text
        result["description"] = sanitized_text
        result["activities"][0]["name"] = sanitized_text
        result["activities"][0]["description"] = sanitized_text
        items = result["activities"][0]["items"]
        assert len(items) == 1
        item = items[0]
        assert item["responseType"] == item_create.response_type
        assert item["name"] == item_create.name
        assert item["question"] == {"en": sanitized_text}
        assert item["isHidden"] == item_create.is_hidden
        assert not item["allowEdit"]

    async def test_create_applet_flow_sanitize_strings(
        self, client: TestClient, applet_minimal_data: AppletCreate, tom: User
    ) -> None:
        client.login(tom)
        text_with_script_inside = "One <script>alert('test')</script> Two"
        sanitized_text = "One  Two"
        data = applet_minimal_data.dict()
        activity_key = data["activities"][0]["key"]
        data["activity_flows"].append(
            dict(
                name=text_with_script_inside,
                description=dict(
                    en=text_with_script_inside,
                ),
                items=[dict(activity_key=activity_key)],
            )
        )
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )

        assert resp.status_code == http.HTTPStatus.CREATED
        result = resp.json()["result"]
        assert result["activityFlows"][0]["name"] == sanitized_text
        assert result["activityFlows"][0]["description"]["en"] == sanitized_text
