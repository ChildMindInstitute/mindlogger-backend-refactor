import copy
import uuid

import pytest

from apps.activities import errors as activity_errors
from apps.activities.domain.response_type_config import ResponseType, SingleSelectionConfig
from apps.activities.domain.response_values import SingleSelectionValues
from apps.applets.domain.applet_create_update import AppletUpdate


class TestActivityItems:
    login_url = "/auth/login"
    applet_list_url = "applets"
    applet_create_url = "workspaces/{owner_id}/applets"
    applet_detail_url = f"{applet_list_url}/{{pk}}"
    activity_detail_url = "activities/{activity_id}"
    applet_workspace_detail_url = "workspaces/{owner_id}/applets/{pk}"

    async def test_creating_applet_with_activity_items(self, client, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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
                            name="activity_item_text",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                        dict(
                            name="activity_item_message",
                            question={"en": "What is your name?"},
                            response_type="message",
                            response_values=None,
                            config=dict(
                                remove_back_button=False,
                                timer=1,
                            ),
                        ),
                        dict(
                            name="activity_item_number_selection",
                            question={"en": "What is your name?"},
                            response_type="numberSelect",
                            response_values=dict(
                                min_value=0,
                                max_value=10,
                            ),
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                            ),
                        ),
                        dict(
                            name="activity_item_time_range",
                            question={"en": "What is your name?"},
                            response_type="timeRange",
                            response_values=None,
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                                timer=1,
                            ),
                        ),
                        dict(
                            name="activity_item_time_range_2",
                            question={"en": "What is your name?"},
                            response_type="time",
                            response_values=None,
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                                timer=1,
                            ),
                        ),
                        dict(
                            name="activity_item_geolocation",
                            question={"en": "What is your name?"},
                            response_type="geolocation",
                            response_values=None,
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                            ),
                        ),
                        dict(
                            name="activity_item_photo",
                            question={"en": "What is your name?"},
                            response_type="photo",
                            response_values=None,
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                            ),
                        ),
                        dict(
                            name="activity_item_video",
                            question={"en": "What is your name?"},
                            response_type="video",
                            response_values=None,
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                            ),
                        ),
                        dict(
                            name="activity_item_date",
                            question={"en": "What is your name?"},
                            response_type="date",
                            response_values=None,
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                            ),
                        ),
                        dict(
                            name="activity_item_drawing",
                            question={"en": "What is your name?"},
                            response_type="drawing",
                            response_values=dict(
                                drawing_background="https://www.w3schools.com/css/img_5terre_wide.jpg",  # noqa E501
                                drawing_example="https://www.w3schools.com/css/img_5terre_wide.jpg",  # noqa E501
                            ),
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                                timer=1,
                                remove_undo_button=False,
                                navigation_to_top=False,
                            ),
                        ),
                        dict(
                            name="activity_item_audio",
                            question={"en": "What is your name?"},
                            response_type="audio",
                            response_values=dict(max_duration=200),
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                                timer=1,
                            ),
                        ),
                        dict(
                            name="activity_item_audioplayer",
                            question={"en": "What is your name?"},
                            response_type="audioPlayer",
                            response_values=dict(
                                file="https://www.w3schools.com/html/horse.mp3",  # noqa E501
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                play_once=False,
                            ),
                        ),
                        dict(
                            name="activity_item_sliderrows",
                            question={"en": "What is your name?"},
                            response_type="sliderRows",
                            response_values=dict(
                                rows=[
                                    {
                                        "label": "label1",
                                        "min_label": "min_label1",
                                        "max_label": "max_label1",
                                        "min_value": 0,
                                        "max_value": 10,
                                        "min_image": None,
                                        "max_image": None,
                                        "score": None,
                                        "alerts": [
                                            dict(
                                                min_value=1,
                                                max_value=4,
                                                alert="alert1",
                                            ),
                                        ],
                                    }
                                ]
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=True,
                                timer=1,
                            ),
                        ),
                        dict(
                            name="activity_item_multiselectionrows",
                            question={"en": "What is your name?"},
                            response_type="multiSelectRows",
                            response_values=dict(
                                rows=[
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9df1",  # noqa E501
                                        "row_name": "row1",
                                        "row_image": None,
                                        "tooltip": None,
                                    },
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9df2",  # noqa E501
                                        "row_name": "row2",
                                        "row_image": None,
                                        "tooltip": None,
                                    },
                                ],
                                options=[
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                        "text": "option1",
                                        "image": None,
                                        "tooltip": None,
                                    },
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9de2",  # noqa E501
                                        "text": "option2",
                                        "image": None,
                                        "tooltip": None,
                                    },
                                ],
                                data_matrix=[
                                    {
                                        "row_id": "17e69155-22cd-4484-8a49-364779ea9df1",  # noqa E501
                                        "options": [
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                                "score": 1,
                                                "alert": None,
                                            },
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de2",  # noqa E501
                                                "score": 2,
                                                "alert": None,
                                            },
                                        ],
                                    },
                                    {
                                        "row_id": "17e69155-22cd-4484-8a49-364779ea9df2",  # noqa E501
                                        "options": [
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                                "score": 3,
                                                "alert": None,
                                            },
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de2",  # noqa E501
                                                "score": 4,
                                                "alert": None,
                                            },
                                        ],
                                    },
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=False,
                                timer=1,
                                add_tooltip=False,
                            ),
                        ),
                        dict(
                            name="activity_item_singleselectionrows",
                            question={"en": "What is your name?"},
                            response_type="singleSelectRows",
                            response_values=dict(
                                rows=[
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9df1",  # noqa E501
                                        "row_name": "row1",
                                        "row_image": None,
                                        "tooltip": None,
                                    },
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9df2",  # noqa E501
                                        "row_name": "row2",
                                        "row_image": None,
                                        "tooltip": None,
                                    },
                                ],
                                options=[
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                        "text": "option1",
                                        "image": None,
                                        "tooltip": None,
                                    },
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9de2",  # noqa E501
                                        "text": "option2",
                                        "image": None,
                                        "tooltip": None,
                                    },
                                ],
                                data_matrix=[
                                    {
                                        "row_id": "17e69155-22cd-4484-8a49-364779ea9df1",  # noqa E501
                                        "options": [
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                                "score": 1,
                                                "alert": "alert1",
                                            },
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de2",  # noqa E501
                                                "score": 2,
                                                "alert": None,
                                            },
                                        ],
                                    },
                                    {
                                        "row_id": "17e69155-22cd-4484-8a49-364779ea9df2",  # noqa E501
                                        "options": [
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                                "score": 3,
                                                "alert": None,
                                            },
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de2",  # noqa E501
                                                "score": 4,
                                                "alert": None,
                                            },
                                        ],
                                    },
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=True,
                                timer=1,
                                add_tooltip=False,
                            ),
                        ),
                        dict(
                            name="activity_item_singleselect",
                            question={"en": "What is your name?"},
                            response_type="singleSelect",
                            response_values=dict(
                                palette_name="palette1",
                                options=[
                                    {
                                        "text": "option1",
                                        "value": 1,
                                        "alert": "alert1",
                                    },
                                    {
                                        "text": "option2",
                                        "value": 2,
                                        "alert": "alert2",
                                    },
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=True,
                                timer=1,
                                add_tooltip=False,
                                set_palette=False,
                                randomize_options=False,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                        dict(
                            name="activity_item_multiselect",
                            question={"en": "What is your name?"},
                            response_type="multiSelect",
                            response_values=dict(
                                palette_name="palette1",
                                options=[
                                    {"text": "option1", "value": 0},
                                    {"text": "option2", "value": 1},
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=False,
                                timer=1,
                                add_tooltip=False,
                                set_palette=False,
                                randomize_options=False,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                        dict(
                            name="activity_item_slideritem",
                            question={"en": "What is your name?"},
                            response_type="slider",
                            response_values=dict(
                                min_value=0,
                                max_value=10,
                                min_label="min_label",
                                max_label="max_label",
                                min_image=None,
                                max_image=None,
                                scores=None,
                                alerts=[
                                    dict(
                                        min_value=1,
                                        max_value=4,
                                        alert="alert1",
                                    ),
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=True,
                                timer=1,
                                show_tick_labels=False,
                                show_tick_marks=False,
                                continuous_slider=True,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                        dict(
                            name="activity_item_slideritem_another",
                            question={"en": "What is your name?"},
                            response_type="slider",
                            response_values=dict(
                                min_value=0,
                                max_value=10,
                                min_label="min_label",
                                max_label="max_label",
                                min_image=None,
                                max_image=None,
                                scores=None,
                                alerts=[
                                    dict(
                                        value="1",
                                        alert="alert1",
                                    ),
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=True,
                                timer=1,
                                show_tick_labels=False,
                                show_tick_marks=False,
                                continuous_slider=False,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                    ],
                ),
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
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await client.get(self.applet_detail_url.format(pk=response.json()["result"]["id"]))
        assert response.status_code == 200

    async def test_creating_applet_with_ab_trails_mobile_activity_items(self, client, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        create_data = dict(
            display_name="mobile_activity_applet",
            encryption=dict(
                public_key=uuid.uuid4().hex,
                prime=uuid.uuid4().hex,
                base=uuid.uuid4().hex,
                account_id=str(uuid.uuid4()),
            ),
            description=dict(
                en="Performance Tasks AB Trails Mobile Applet",
                fr="Performance Tasks AB Trails Mobile Applet",
            ),
            about=dict(
                en="Applet AB Trails Mobile Task Builder Activity",
                fr="Applet AB Trails Mobile Task Builder Activity",
            ),
            activities=[
                dict(
                    name="Activity_ABTrailsMobile",
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Description Activity ABTrailsMobile.",
                        fr="Description Activity ABTrailsMobile.",
                    ),
                    items=[
                        dict(
                            name="AB_Trails_Mobile_1",
                            question=dict(
                                en="ab_trails_mobile 1 question",
                                fr="ab_trails_mobile 1 question",
                            ),
                            response_type="ABTrails",
                            response_values=None,
                            config=dict(
                                device_type="mobile",
                                order_name="first",
                            ),
                        ),
                        dict(
                            name="AB_Trails_Mobile_2",
                            question=dict(
                                en="ab_trails_mobile 2 question",
                                fr="ab_trails_mobile 2 question",
                            ),
                            response_type="ABTrails",
                            response_values=None,
                            config=dict(
                                device_type="mobile",
                                order_name="second",
                            ),
                        ),
                        dict(
                            name="AB_Trails_Mobile_3",
                            question=dict(
                                en="ab_trails_mobile 3 question",
                                fr="ab_trails_mobile 3 question",
                            ),
                            response_type="ABTrails",
                            response_values=None,
                            config=dict(
                                device_type="mobile",
                                order_name="third",
                            ),
                        ),
                        dict(
                            name="AB_Trails_Mobile_4",
                            question=dict(
                                en="ab_trails_mobile 4 question",
                                fr="ab_trails_mobile 4 question",
                            ),
                            response_type="ABTrails",
                            response_values=None,
                            config=dict(
                                device_type="mobile",
                                order_name="fourth",
                            ),
                        ),
                    ],
                ),
            ],
            activity_flows=[
                dict(
                    name="name_activityFlow",
                    description=dict(
                        en="description activityFlow",
                        fr="description activityFlow",
                    ),
                    items=[dict(activity_key="577dbbda-3afc-" "4962-842b-8d8d11588bfe")],
                )
            ],
        )
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await client.get(self.applet_detail_url.format(pk=response.json()["result"]["id"]))
        assert response.status_code == 200

    async def test_creating_applet_with_ab_trails_tablet_activity_items(self, client, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        create_data = dict(
            display_name="tablet_activity_applet",
            encryption=dict(
                public_key=uuid.uuid4().hex,
                prime=uuid.uuid4().hex,
                base=uuid.uuid4().hex,
                account_id=str(uuid.uuid4()),
            ),
            description=dict(
                en="Performance Tasks AB Trails Tablet Applet",
                fr="Performance Tasks AB Trails Tablet Applet",
            ),
            about=dict(
                en="Applet AB Trails Tablet Task Builder Activity",
                fr="Applet AB Trails Tablet Task Builder Activity",
            ),
            activities=[
                dict(
                    name="Activity_ABTrailsTablet",
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Description Activity ABTrailsTablet.",
                        fr="Description Activity ABTrailsTablet.",
                    ),
                    items=[
                        dict(
                            name="AB_Trails_Tablet_1",
                            question=dict(
                                en="ab_trails_tablet 1 question",
                                fr="ab_trails_tablet 1 question",
                            ),
                            response_type="ABTrails",
                            response_values=None,
                            config=dict(
                                device_type="tablet",
                                order_name="first",
                            ),
                        ),
                        dict(
                            name="AB_Trails_Tablet_2",
                            question=dict(
                                en="ab_trails_tablet 2 question",
                                fr="ab_trails_tablet 2 question",
                            ),
                            response_type="ABTrails",
                            response_values=None,
                            config=dict(
                                device_type="tablet",
                                order_name="second",
                            ),
                        ),
                        dict(
                            name="AB_Trails_Tablet_3",
                            question=dict(
                                en="ab_trails_tablet 3 question",
                                fr="ab_trails_tablet 3 question",
                            ),
                            response_type="ABTrails",
                            response_values=None,
                            config=dict(
                                device_type="tablet",
                                order_name="third",
                            ),
                        ),
                        dict(
                            name="AB_Trails_Tablet_4",
                            question=dict(
                                en="ab_trails_tablet 4 question",
                                fr="ab_trails_tablet 4 question",
                            ),
                            response_type="ABTrails",
                            response_values=None,
                            config=dict(
                                device_type="tablet",
                                order_name="fourth",
                            ),
                        ),
                    ],
                ),
            ],
            activity_flows=[
                dict(
                    name="name_activityFlow",
                    description=dict(
                        en="description activityFlow",
                        fr="description activityFlow",
                    ),
                    items=[dict(activity_key="577dbbda-3afc-" "4962-842b-8d8d11588bfe")],
                )
            ],
        )
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await client.get(self.applet_detail_url.format(pk=response.json()["result"]["id"]))
        assert response.status_code == 200

    async def test_creating_applet_with_gyroscope_activity_items(self, client, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        create_data = dict(
            display_name="gyroscope_activity_applet",
            encryption=dict(
                public_key=uuid.uuid4().hex,
                prime=uuid.uuid4().hex,
                base=uuid.uuid4().hex,
                account_id=str(uuid.uuid4()),
            ),
            description=dict(
                en="Performance Tasks CST Gyroscope Applet",
                fr="Performance Tasks CST Gyroscope Applet",
            ),
            about=dict(
                en="Applet CST Gyroscope Task Builder Activity",
                fr="Applet CST Gyroscope Task Builder Activity",
            ),
            activities=[
                dict(
                    name="Activity_gyroscope",
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Description Activity gyroscope.",
                        fr="Description Activity gyroscope.",
                    ),
                    items=[
                        dict(
                            name="Gyroscope_General_instruction",
                            question=dict(
                                en="Gyroscope General instruction text.",
                                fr="Gyroscope General instruction text.",
                            ),
                            response_type="message",
                            response_values=None,
                            config=dict(
                                remove_back_button=False,
                                timer=None,
                            ),
                        ),
                        dict(
                            name="Gyroscope_Сalibration_Practice_instruction",
                            question=dict(
                                en="Gyroscope Сalibration/Practice " "instruction text.",
                                fr="Gyroscope Сalibration/Practice " "instruction text.",
                            ),
                            response_type="message",
                            response_values=None,
                            config=dict(
                                remove_back_button=False,
                                timer=None,
                            ),
                        ),
                        dict(
                            name="Gyroscope_Сalibration_Practice",
                            question=dict(
                                en="Gyroscope Сalibration/Practice.",
                                fr="Gyroscope Сalibration/Practice.",
                            ),
                            response_type="stabilityTracker",
                            response_values=None,
                            config=dict(
                                user_input_type="gyroscope",
                                phase="practice",
                                trials_number=3,
                                duration_minutes=5,
                                lambda_slope=0.2,
                                max_off_target_time=10,
                                num_test_trials=10,
                                task_mode="pseudo_stair",
                                tracking_dims=2,
                                show_score=True,
                                basis_func="zeros_1d",
                                noise_level=0,
                                task_loop_rate=0.0167,
                                cycles_per_min=2,
                                oob_duration=0.2,
                                initial_lambda=0.075,
                                show_preview=True,
                                num_preview_stim=0,
                                preview_step_gap=100,
                                dimension_count=1,
                                max_rad=0.26167,
                            ),
                        ),
                        dict(
                            name="Gyroscope_Test_instruction",
                            question=dict(
                                en="Gyroscope Test instruction text.",
                                fr="Gyroscope Test instruction text.",
                            ),
                            response_type="message",
                            response_values=None,
                            config=dict(
                                remove_back_button=False,
                                timer=None,
                            ),
                        ),
                        dict(
                            name="Gyroscope_Test",
                            question=dict(
                                en="Gyroscope Test.",
                                fr="Gyroscope Test.",
                            ),
                            response_type="stabilityTracker",
                            response_values=None,
                            config=dict(
                                user_input_type="gyroscope",
                                phase="test",
                                trials_number=5,
                                duration_minutes=7,
                                lambda_slope=0.2,
                                max_off_target_time=10,
                                num_test_trials=10,
                                task_mode="pseudo_stair",
                                tracking_dims=2,
                                show_score=True,
                                basis_func="zeros_1d",
                                noise_level=0,
                                task_loop_rate=0.0167,
                                cycles_per_min=2,
                                oob_duration=0.2,
                                initial_lambda=0.075,
                                show_preview=True,
                                num_preview_stim=0,
                                preview_step_gap=100,
                                dimension_count=1,
                                max_rad=0.26167,
                            ),
                        ),
                    ],
                ),
            ],
            activity_flows=[
                dict(
                    name="name_activityFlow",
                    description=dict(
                        en="description activityFlow",
                        fr="description activityFlow",
                    ),
                    items=[dict(activity_key="577dbbda-3afc-" "4962-842b-8d8d11588bfe")],
                )
            ],
        )
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await client.get(self.applet_detail_url.format(pk=response.json()["result"]["id"]))
        assert response.status_code == 200

    async def test_creating_applet_with_touch_activity_items(self, client, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        create_data = dict(
            display_name="touch_activity_applet",
            encryption=dict(
                public_key=uuid.uuid4().hex,
                prime=uuid.uuid4().hex,
                base=uuid.uuid4().hex,
                account_id=str(uuid.uuid4()),
            ),
            description=dict(
                en="Performance Tasks CST Touch Applet",
                fr="Performance Tasks CST Touch Applet",
            ),
            about=dict(
                en="Applet CST Touch Task Builder Activity",
                fr="Applet CST Touch Task Builder Activity",
            ),
            activities=[
                dict(
                    name="Activity_touch",
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Description Activity touch.",
                        fr="Description Activity touch.",
                    ),
                    items=[
                        dict(
                            name="Touch_General_instruction",
                            question=dict(
                                en="Touch General instruction text.",
                                fr="Touch General instruction text.",
                            ),
                            response_type="message",
                            response_values=None,
                            config=dict(
                                remove_back_button=False,
                                timer=None,
                            ),
                        ),
                        dict(
                            name="Touch_Сalibration_Practice_instruction",
                            question=dict(
                                en="Touch Сalibration/Practice " "instruction text.",
                                fr="Touch Сalibration/Practice " "instruction text.",
                            ),
                            response_type="message",
                            response_values=None,
                            config=dict(
                                remove_back_button=False,
                                timer=None,
                            ),
                        ),
                        dict(
                            name="Touch_Сalibration_Practice",
                            question=dict(
                                en="Touch Сalibration/Practise.",
                                fr="Touch Сalibration/Practise.",
                            ),
                            response_type="stabilityTracker",
                            response_values=None,
                            config=dict(
                                user_input_type="touch",
                                phase="practice",
                                trials_number=3,
                                duration_minutes=5,
                                lambda_slope=0.2,
                                max_off_target_time=10,
                                num_test_trials=10,
                                task_mode="pseudo_stair",
                                tracking_dims=2,
                                show_score=True,
                                basis_func="zeros_1d",
                                noise_level=0,
                                task_loop_rate=0.0167,
                                cycles_per_min=2,
                                oob_duration=0.2,
                                initial_lambda=0.075,
                                show_preview=True,
                                num_preview_stim=0,
                                preview_step_gap=100,
                                dimension_count=1,
                                max_rad=0.26167,
                            ),
                        ),
                        dict(
                            name="Touch_Test_instruction",
                            question=dict(
                                en="Touch Test instruction text.",
                                fr="Touch Test instruction text.",
                            ),
                            response_type="message",
                            response_values=None,
                            config=dict(
                                remove_back_button=False,
                                timer=None,
                            ),
                        ),
                        dict(
                            name="Touch_Test",
                            question=dict(
                                en="Touch Test.",
                                fr="Touch Test.",
                            ),
                            response_type="stabilityTracker",
                            response_values=None,
                            config=dict(
                                user_input_type="touch",
                                phase="test",
                                trials_number=5,
                                duration_minutes=7,
                                lambda_slope=0.2,
                                max_off_target_time=10,
                                num_test_trials=10,
                                task_mode="pseudo_stair",
                                tracking_dims=2,
                                show_score=True,
                                basis_func="zeros_1d",
                                noise_level=0,
                                task_loop_rate=0.0167,
                                cycles_per_min=2,
                                oob_duration=0.2,
                                initial_lambda=0.075,
                                show_preview=True,
                                num_preview_stim=0,
                                preview_step_gap=100,
                                dimension_count=1,
                                max_rad=0.26167,
                            ),
                        ),
                    ],
                ),
            ],
            activity_flows=[
                dict(
                    name="name_activityFlow",
                    description=dict(
                        en="description activityFlow",
                        fr="description activityFlow",
                    ),
                    items=[dict(activity_key="577dbbda-3afc-" "4962-842b-8d8d11588bfe")],
                )
            ],
        )
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await client.get(self.applet_detail_url.format(pk=response.json()["result"]["id"]))
        assert response.status_code == 200

    async def test_creating_applet_with_activity_items_condition(self, client, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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
                # Activity with conditional logic
                dict(
                    name="Morning activity with conditional logic",
                    key="577dbbdd-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                        fr="Understand morning feelings.",
                    ),
                    subscale_setting=dict(
                        calculate_total_score="sum",
                        total_scores_table_data=[
                            dict(
                                raw_score="1",
                                optional_text="optional_text",
                            ),
                            dict(
                                raw_score="2",
                                optional_text="optional_text2",
                            ),
                        ],
                        subscales=[
                            dict(
                                name="subscale1",
                                scoring="sum",
                                items=[
                                    dict(
                                        name="activity_item_singleselect",
                                        type="item",
                                    ),
                                ],
                                subscale_table_data=[
                                    dict(
                                        score="1.2342~1231",
                                        raw_score="1",
                                        age=15,
                                        sex="F",
                                        optional_text="optional_text",
                                    ),
                                    dict(
                                        score="1.2342~1231.12333",
                                        raw_score="1~6",
                                        age=10,
                                        sex="M",
                                        optional_text="optional_text12",
                                    ),
                                    dict(
                                        score=1,
                                        raw_score=1,
                                        age=15,
                                        sex="M",
                                        optional_text="optional_text13",
                                    ),
                                ],
                            ),
                            dict(
                                name="subscale12",
                                scoring="sum",
                                items=[
                                    dict(
                                        name="activity_item_singleselect",
                                        type="item",
                                    ),
                                    dict(
                                        name="subscale1",
                                        type="subscale",
                                    ),
                                ],
                                subscale_table_data=[
                                    dict(
                                        score="1.2342~1231",
                                        raw_score="1",
                                        age=15,
                                        sex="F",
                                        optional_text="optional_text",
                                    ),
                                    dict(
                                        score="1.2342~1231.12333",
                                        raw_score="1~6",
                                        age=10,
                                        sex="M",
                                        optional_text="optional_text12",
                                    ),
                                    dict(
                                        score=1,
                                        raw_score=1,
                                        age=15,
                                        sex="M",
                                        optional_text="optional_text13",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    scores_and_reports=dict(
                        generateReport=True,
                        showScoreSummary=True,
                        reports=[
                            dict(
                                name="activity_item_singleselect_score",
                                type="score",
                                id="activity_item_singleselect_score",
                                calculationType="sum",
                                minScore=0,
                                maxScore=3,
                                itemsScore=["activity_item_singleselect"],
                                message="Hello",
                                itemsPrint=[
                                    "activity_item_singleselect",
                                    "activity_item_multiselect",
                                    "activity_item_slideritem",
                                    "activity_item_text",
                                ],
                                conditionalLogic=[
                                    dict(
                                        name="score1_condition1",
                                        id="activity_item_singleselect_score",
                                        flagScore=True,
                                        message="Hello2",
                                        match="any",
                                        conditions=[
                                            dict(
                                                item_name=("activity_item_" "singleselect_score"),
                                                type="GREATER_THAN",
                                                payload=dict(
                                                    value=1,
                                                ),
                                            ),
                                            dict(
                                                item_name=("activity_item_" "singleselect_score"),
                                                type="GREATER_THAN",
                                                payload=dict(
                                                    value=1,
                                                ),
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            dict(
                                name="section1",
                                type="section",
                                messages="Hello from the other side",
                                itemsPrint=[
                                    "activity_item_singleselect",
                                    "activity_item_multiselect",
                                    "activity_item_slideritem",
                                    "activity_item_text",
                                ],
                                conditionalLogic=dict(
                                    match="all",
                                    conditions=[
                                        dict(
                                            item_name=(
                                                "activity_item_singleselect_score"  # noqa E501
                                            ),
                                            type="GREATER_THAN",
                                            payload=dict(
                                                value=1,
                                            ),
                                        ),
                                        dict(
                                            item_name=(
                                                "activity_item_singleselect_score"  # noqa E501
                                            ),
                                            type="EQUAL_TO_OPTION",
                                            payload=dict(
                                                option_value="1",  # noqa E501
                                            ),
                                        ),
                                        dict(
                                            item_name=(
                                                "activity_item_singleselect_score"  # noqa E501
                                            ),
                                            type="NOT_EQUAL_TO_OPTION",
                                            payload=dict(
                                                option_value="2",  # noqa E501
                                            ),
                                        ),
                                        dict(
                                            item_name=(
                                                "activity_item_multiselect"  # noqa E501
                                            ),
                                            type="NOT_INCLUDES_OPTION",
                                            payload=dict(
                                                option_value="1",  # noqa E501
                                            ),
                                        ),
                                    ],
                                ),
                            ),
                        ],
                    ),
                    items=[
                        dict(
                            name="activity_item_singleselect",
                            question={"en": "What is your name?"},
                            response_type="singleSelect",
                            response_values=dict(
                                palette_name="palette1",
                                options=[
                                    {
                                        "text": "option1",
                                        "score": 1,
                                        "id": "25e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                        "value": "1",
                                    },
                                    {
                                        "text": "option2",
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
                                timer=1,
                                add_tooltip=False,
                                set_palette=False,
                                randomize_options=False,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                        dict(
                            name="activity_item_text",
                            question=dict(
                                en="How had you slept?",
                                fr="How had you slept?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                            conditional_logic=dict(
                                match="any",
                                conditions=[
                                    dict(
                                        item_name="activity_item_singleselect",
                                        type="EQUAL_TO_OPTION",
                                        payload=dict(
                                            option_value="1"  # noqa E501
                                        ),
                                    ),
                                    dict(
                                        item_name="activity_item_singleselect_2",
                                        type="NOT_EQUAL_TO_OPTION",
                                        payload=dict(
                                            option_value="2"  # noqa E501
                                        ),
                                    ),
                                    dict(
                                        item_name="activity_item_multiselect",
                                        type="INCLUDES_OPTION",
                                        payload=dict(
                                            option_value="1"  # noqa E501
                                        ),
                                    ),
                                    dict(
                                        item_name="activity_item_multiselect_2",
                                        type="NOT_INCLUDES_OPTION",
                                        payload=dict(
                                            option_value="2"  # noqa E501
                                        ),
                                    ),
                                    dict(
                                        item_name="activity_item_slideritem",
                                        type="GREATER_THAN",
                                        payload=dict(
                                            value=5,
                                        ),
                                    ),
                                    dict(
                                        item_name="activity_item_slideritem_2",
                                        type="OUTSIDE_OF",
                                        payload=dict(
                                            min_value=5,
                                            max_value=10,
                                        ),
                                    ),
                                ],
                            ),
                        ),
                        dict(
                            name="activity_item_singleselect_2",
                            question={"en": "What is your name?"},
                            response_type="singleSelect",
                            response_values=dict(
                                palette_name="palette1",
                                options=[
                                    {
                                        "text": "option1",
                                        "score": 1,
                                        "id": "25e69155-22cd-4484-8a49-364779fa9de1",  # noqa E501
                                        "value": "1",
                                    },
                                    {
                                        "text": "option2",
                                        "score": 2,
                                        "id": "26e69155-22cd-4484-8a49-364779fa9de1",  # noqa E501
                                        "value": "2",
                                    },
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=True,
                                set_alerts=False,
                                timer=1,
                                add_tooltip=False,
                                set_palette=False,
                                randomize_options=False,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                        dict(
                            name="activity_item_multiselect",
                            question={"en": "What is your name?"},
                            response_type="multiSelect",
                            response_values=dict(
                                palette_name="palette1",
                                options=[
                                    {
                                        "text": "option1",
                                        "id": "27e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                        "value": "1",
                                    },
                                    {
                                        "text": "option2",
                                        "id": "28e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                        "value": "2",
                                    },
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=False,
                                timer=1,
                                add_tooltip=False,
                                set_palette=False,
                                randomize_options=False,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                        dict(
                            name="activity_item_multiselect_2",
                            question={"en": "Option 2?"},
                            response_type="multiSelect",
                            response_values=dict(
                                palette_name="palette1",
                                options=[
                                    {
                                        "text": "option1",
                                        "id": "27e69155-22cd-4484-8a49-364779eb9de1",  # noqa E501
                                        "value": "1",
                                    },
                                    {
                                        "text": "option2",
                                        "id": "28e69155-22cd-4484-8a49-364779eb9de1",  # noqa E501
                                        "value": "2",
                                    },
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=False,
                                timer=1,
                                add_tooltip=False,
                                set_palette=False,
                                randomize_options=False,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                        dict(
                            name="activity_item_slideritem",
                            question={"en": "What is your name?"},
                            response_type="slider",
                            response_values=dict(
                                min_value=0,
                                max_value=10,
                                min_label="min_label",
                                max_label="max_label",
                                min_image=None,
                                max_image=None,
                                scores=None,
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=False,
                                timer=1,
                                show_tick_labels=False,
                                show_tick_marks=False,
                                continuous_slider=False,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                        dict(
                            name="activity_item_slideritem_2",
                            question={"en": "What is your name?"},
                            response_type="slider",
                            response_values=dict(
                                min_value=0,
                                max_value=10,
                                min_label="min_label",
                                max_label="max_label",
                                min_image=None,
                                max_image=None,
                                scores=None,
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=False,
                                timer=1,
                                show_tick_labels=False,
                                show_tick_marks=False,
                                continuous_slider=False,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                        dict(
                            name="activity_item_time_range",
                            question={"en": "What is your name?"},
                            response_type="timeRange",
                            response_values=None,
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                                timer=1,
                            ),
                            conditional_logic=dict(
                                match="all",
                                conditions=[
                                    dict(
                                        item_name="activity_item_singleselect",
                                        type="EQUAL_TO_OPTION",
                                        payload=dict(
                                            option_value="1"  # noqa E501
                                        ),
                                    ),
                                ],
                            ),
                        ),
                        dict(
                            name="activity_item_time_range_2",
                            question={"en": "What is your name?"},
                            response_type="time",
                            response_values=None,
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                                timer=1,
                            ),
                            conditional_logic=dict(
                                match="all",
                                conditions=[
                                    dict(
                                        item_name="activity_item_singleselect",
                                        type="EQUAL_TO_OPTION",
                                        payload=dict(
                                            option_value="1"  # noqa E501
                                        ),
                                    ),
                                    dict(
                                        item_name="activity_item_multiselect",
                                        type="INCLUDES_OPTION",
                                        payload=dict(
                                            option_value="1"  # noqa E501
                                        ),
                                    ),
                                ],
                            ),
                        ),
                        dict(
                            name="activity_item_audio",
                            question={"en": "What is your name?"},
                            response_type="audio",
                            response_values=dict(max_duration=200),
                            config=dict(
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                                remove_back_button=False,
                                skippable_item=False,
                                timer=1,
                            ),
                        ),
                    ],
                ),
            ],
            activity_flows=[
                dict(
                    name="Morning questionnaire",
                    description=dict(
                        en="Understand how was the morning",
                        fr="Understand how was the morning",
                    ),
                    items=[
                        dict(
                            activity_key="577dbbdd-3afc-4962-842b-8d8d11588bfe"  # noqa E501
                        )
                    ],
                )
            ],
        )
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=create_data,
        )
        assert response.status_code == 400
        assert response.json()["result"][0]["message"] == activity_errors.IncorrectConditionItemIndexError.message

        text_item = create_data["activities"][0]["items"][1]
        slider_item_2 = create_data["activities"][0]["items"][6]
        create_data["activities"][0]["items"][1] = slider_item_2
        create_data["activities"][0]["items"][6] = text_item

        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=create_data,
        )
        assert response.status_code == 201, response.json()
        assert isinstance(
            response.json()["result"]["activities"][0]["items"][6]["conditionalLogic"],
            dict,
        )
        assert isinstance(
            response.json()["result"]["activities"][0]["scoresAndReports"],
            dict,
        )
        assert isinstance(response.json()["result"]["activities"][0]["subscaleSetting"], dict)

        response = await client.get(self.applet_detail_url.format(pk=response.json()["result"]["id"]))
        assert response.status_code == 200

        activity_id = response.json()["result"]["activities"][0]["id"]
        response = await client.get(self.activity_detail_url.format(activity_id=activity_id))
        assert response.status_code == 200
        assert isinstance(response.json()["result"]["items"][6]["conditionalLogic"], dict)

    async def test_creating_activity_items_without_option_value(self, client, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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
                            name="activity_item_sliderrows",
                            question={"en": "What is your name?"},
                            response_type="sliderRows",
                            response_values=dict(
                                rows=[
                                    {
                                        "label": "label1",
                                        "min_label": "min_label1",
                                        "max_label": "max_label1",
                                        "min_value": 0,
                                        "max_value": 10,
                                        "min_image": None,
                                        "max_image": None,
                                        "score": None,
                                        "alerts": [
                                            dict(
                                                min_value=1,
                                                max_value=4,
                                                alert="alert1",
                                            ),
                                        ],
                                    }
                                ]
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=True,
                                timer=1,
                            ),
                        ),
                        dict(
                            name="activity_item_singleselectionrows",
                            question={"en": "What is your name?"},
                            response_type="singleSelectRows",
                            response_values=dict(
                                rows=[
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9df1",  # noqa E501
                                        "row_name": "row1",
                                        "row_image": None,
                                        "tooltip": None,
                                    },
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9df2",  # noqa E501
                                        "row_name": "row2",
                                        "row_image": None,
                                        "tooltip": None,
                                    },
                                ],
                                options=[
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                        "text": "option1",
                                        "image": None,
                                        "tooltip": None,
                                    },
                                    {
                                        "id": "17e69155-22cd-4484-8a49-364779ea9de2",  # noqa E501
                                        "text": "option2",
                                        "image": None,
                                        "tooltip": None,
                                    },
                                ],
                                data_matrix=[
                                    {
                                        "row_id": "17e69155-22cd-4484-8a49-364779ea9df1",  # noqa E501
                                        "options": [
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                                "score": 1,
                                                "alert": "alert1",
                                            },
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de2",  # noqa E501
                                                "score": 2,
                                                "alert": None,
                                            },
                                        ],
                                    },
                                    {
                                        "row_id": "17e69155-22cd-4484-8a49-364779ea9df2",  # noqa E501
                                        "options": [
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de1",  # noqa E501
                                                "score": 3,
                                                "alert": None,
                                            },
                                            {
                                                "option_id": "17e69155-22cd-4484-8a49-364779ea9de2",  # noqa E501
                                                "score": 4,
                                                "alert": None,
                                            },
                                        ],
                                    },
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=True,
                                timer=1,
                                add_tooltip=False,
                            ),
                        ),
                        dict(
                            name="activity_item_slideritem",
                            question={"en": "What is your name?"},
                            response_type="slider",
                            response_values=dict(
                                min_value=0,
                                max_value=10,
                                min_label="min_label",
                                max_label="max_label",
                                min_image=None,
                                max_image=None,
                                scores=None,
                                alerts=[
                                    dict(
                                        min_value=1,
                                        max_value=4,
                                        alert="alert1",
                                    ),
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=True,
                                timer=1,
                                show_tick_labels=False,
                                show_tick_marks=False,
                                continuous_slider=True,
                                additional_response_option={
                                    "text_input_option": False,
                                    "text_input_required": False,
                                },
                            ),
                        ),
                        dict(
                            name="activity_item_singleselect",
                            question={"en": "What is your name?"},
                            response_type="singleSelect",
                            response_values=dict(
                                palette_name="palette1",
                                options=[
                                    {
                                        "text": "option1",
                                        "alert": "alert1",
                                        "value": 0,
                                    },
                                    {
                                        "text": "option2",
                                        "alert": "alert2",
                                        "value": 1,
                                    },
                                ],
                            ),
                            config=dict(
                                remove_back_button=False,
                                skippable_item=False,
                                add_scores=False,
                                set_alerts=True,
                                timer=1,
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
                ),
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
        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await client.get(self.applet_detail_url.format(pk=response.json()["result"]["id"]))
        assert response.status_code == 200
        applet_id = response.json()["result"]["id"]

        response = await client.get(
            self.activity_detail_url.format(activity_id=response.json()["result"]["activities"][0]["id"])
        )
        slider_rows_id = response.json()["result"]["items"][0]["id"]

        assert response.status_code == 200
        assert response.json()["result"]["items"][3]["responseValues"]["options"][0]["value"] == 0

        create_data["activities"][0]["items"][0] = dict(
            id=slider_rows_id,
            name="activity_item_sliderrows",
            question={"en": "What is your name?"},
            response_type="sliderRows",
            response_values=dict(
                rows=[
                    {
                        "label": "label1",
                        "min_label": "min_label1",
                        "max_label": "max_label1",
                        "min_value": 1,
                        "max_value": 5,
                        "min_image": None,
                        "max_image": None,
                        "scores": [1, 2, 3, 4, 5],
                    }
                ]
            ),
            config=dict(
                remove_back_button=False,
                skippable_item=False,
                add_scores=True,
                set_alerts=True,
                timer=1,
            ),
        )

        response = await client.put(
            self.applet_detail_url.format(pk=applet_id),
            data=create_data,
        )
        assert response.status_code == 200

    async def test_create_applet_with_flanker_preformance_task(self, client, activity_flanker_data, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            display_name="Flanker",
            encryption=dict(
                public_key=uuid.uuid4().hex,
                prime=uuid.uuid4().hex,
                base=uuid.uuid4().hex,
                account_id=str(uuid.uuid4()),
            ),
            description=dict(en="Flanker", fr="Flanker"),
            about=dict(en="Flanker", fr="Flanker"),
            activities=[activity_flanker_data],
            # Empty, but required
            activity_flows=[],
        )

        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        assert response.json()["result"]["activities"][0]["isPerformanceTask"]
        assert response.json()["result"]["activities"][0]["performanceTaskType"] == "flanker"

        # Check that the 'get' after creating new applet returns correct data
        response = await client.get(
            self.applet_workspace_detail_url.format(
                owner_id=tom.id,
                pk=response.json()["result"]["id"],
            )
        )
        assert response.status_code == 200
        assert response.json()["result"]["activities"][0]["isPerformanceTask"]
        assert response.json()["result"]["activities"][0]["performanceTaskType"] == "flanker"

    async def test_applet_add_performance_task_to_the_applet(self, client, activity_flanker_data, tom):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")

        create_data = dict(
            display_name="Add flanker to existing applet",
            encryption=dict(
                public_key=uuid.uuid4().hex,
                prime=uuid.uuid4().hex,
                base=uuid.uuid4().hex,
                account_id=str(uuid.uuid4()),
            ),
            description=dict(en="Add flanker to existing applet"),
            about=dict(en="Add flanker to existing applet"),
            activities=[
                dict(
                    name="Morning activity",
                    key="577dbbda-3afc-4962-842b-8d8d11588bfe",
                    description=dict(
                        en="Understand morning feelings.",
                    ),
                    items=[
                        dict(
                            name="activity_item_text",
                            question=dict(
                                en="How had you slept?",
                            ),
                            response_type="text",
                            response_values=None,
                            config=dict(
                                max_response_length=200,
                                correct_answer_required=False,
                                correct_answer=None,
                                numerical_response_required=False,
                                response_data_identifier=False,
                                response_required=False,
                                remove_back_button=False,
                                skippable_item=True,
                            ),
                        ),
                    ],
                ),
            ],
            # Empty, but required
            activity_flows=[],
        )

        response = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=create_data,
        )
        assert response.status_code == 201
        activity = response.json()["result"]["activities"][0]
        assert not activity["isPerformanceTask"]
        assert not activity["performanceTaskType"]
        # Test that get after creating new applet returns correct data
        # Generaly we don't need to test, tested data, but for now let leave
        # it here
        response = await client.get(
            self.applet_workspace_detail_url.format(
                owner_id=tom.id,
                pk=response.json()["result"]["id"],
            )
        )
        assert response.status_code == 200
        activity = response.json()["result"]["activities"][0]
        assert not activity["isPerformanceTask"]
        assert not activity["performanceTaskType"]

        # Add flanker performance task
        create_data["activities"].append(activity_flanker_data)

        response = await client.put(
            self.applet_detail_url.format(pk=response.json()["result"]["id"]),
            data=create_data,
        )
        assert response.status_code == 200
        flanker = response.json()["result"]["activities"][1]
        assert flanker["isPerformanceTask"]
        assert flanker["performanceTaskType"] == "flanker"

        # Check the 'get' method
        response = await client.get(
            self.applet_workspace_detail_url.format(
                owner_id=tom.id,
                pk=response.json()["result"]["id"],
            )
        )
        assert response.status_code == 200
        flanker = response.json()["result"]["activities"][1]
        assert flanker["isPerformanceTask"]
        assert flanker["performanceTaskType"] == "flanker"

    # TODO: move all validation test to the activity domain test
    async def test_create_applet_item_name_is_not_valid(self, client, applet_minimal_data, tom) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
        data["activities"][0]["items"][0]["name"] = "%name"
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == activity_errors.IncorrectNameCharactersError.message

    async def test_create_applet_item_config_not_valid(self, client, applet_minimal_data, tom) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
        del data["activities"][0]["items"][0]["config"]["add_scores"]
        del data["activities"][0]["items"][0]["config"]["set_alerts"]
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == activity_errors.IncorrectConfigError.message.format(type=SingleSelectionConfig)

    async def test_create_applet_not_valid_response_type(self, client, applet_minimal_data, tom) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
        data["activities"][0]["items"][0]["response_type"] = "NotValid"
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == activity_errors.IncorrectResponseValueError.message.format(type=ResponseType)

    @pytest.mark.parametrize(
        "value,error_msg",
        (
            (
                {},
                activity_errors.IncorrectResponseValueError.message.format(type=SingleSelectionValues),
            ),
            (
                None,
                activity_errors.IncorrectResponseValueError.message.format(type=SingleSelectionValues),
            ),
        ),
    )
    async def test_create_applet_not_valid_response_values(
        self, client, applet_minimal_data, tom, value, error_msg
    ) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
        data["activities"][0]["items"][0]["response_values"] = value
        data["activities"][0]["items"][0]["response_type"] = ResponseType.SINGLESELECT
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == error_msg

    async def test_create_applet_without_item_response_type(self, client, applet_minimal_data, tom) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
        del data["activities"][0]["items"][0]["response_type"]
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == "field required"

    async def test_create_applet_single_select_add_scores_not_scores_in_response_values(
        self, client, applet_minimal_data, tom
    ) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
        data["activities"][0]["items"][0]["config"]["add_scores"] = True
        data["activities"][0]["items"][0]["response_type"] = ResponseType.SINGLESELECT
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == activity_errors.ScoreRequiredForResponseValueError.message

    async def test_create_applet_slider_response_values_add_scores_not_scores_in_response_values(
        self, client, applet_minimal_data, slider_response_values, slider_config, tom
    ) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
        slider_config.add_scores = True
        data["activities"][0]["items"][0]["config"] = slider_config.dict()
        data["activities"][0]["items"][0]["response_type"] = ResponseType.SLIDER
        data["activities"][0]["items"][0]["response_values"] = slider_response_values.dict()
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == activity_errors.NullScoreError.message

    async def test_create_applet_slider_response_values_add_scores_scores_not_for_all_values(
        self, client, applet_minimal_data, slider_response_values, slider_config, tom
    ) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
        slider_config.add_scores = True
        min_val = slider_response_values.min_value
        max_val = slider_response_values.max_value
        scores = [i for i in range(max_val - min_val)]
        slider_response_values_data = slider_response_values.dict()
        slider_response_values_data["scores"] = scores
        data["activities"][0]["items"][0]["config"] = slider_config.dict()
        data["activities"][0]["items"][0]["response_type"] = ResponseType.SLIDER
        data["activities"][0]["items"][0]["response_values"] = slider_response_values_data
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == activity_errors.InvalidScoreLengthError.message

    async def test_create_applet_slider_rows_response_values_add_scores_true_no_scores(
        self, client, applet_minimal_data, slider_rows_response_values, slider_rows_config, tom
    ) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
        slider_rows_config_data = slider_rows_config.dict()
        slider_rows_response_values_data = slider_rows_response_values.dict()
        slider_rows_config_data["add_scores"] = True
        slider_rows_response_values_data["rows"][0]["scores"] = None
        item = data["activities"][0]["items"][0]
        item["config"] = slider_rows_config_data
        item["response_type"] = ResponseType.SLIDERROWS
        item["response_values"] = slider_rows_response_values_data
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == activity_errors.NullScoreError.message

    async def test_create_applet_slider_rows_response_values_add_scores_true_scores_not_for_all_values(
        self, client, applet_minimal_data, slider_rows_response_values, slider_rows_config, tom
    ) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
        slider_rows_response_values_data = slider_rows_response_values.dict()
        slider_rows_config_data = slider_rows_config.dict()
        slider_rows_config_data["add_scores"] = True
        min_val = slider_rows_response_values_data["rows"][0]["min_value"]
        max_val = slider_rows_response_values_data["rows"][0]["max_value"]
        slider_rows_response_values_data["rows"][0]["scores"] = [i for i in range(max_val - min_val)]
        item = data["activities"][0]["items"][0]
        item["config"] = slider_rows_config_data
        item["response_type"] = ResponseType.SLIDERROWS
        item["response_values"] = slider_rows_response_values_data
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == activity_errors.InvalidScoreLengthError.message

    @pytest.mark.parametrize("response_type", (ResponseType.SINGLESELECT, ResponseType.MULTISELECT))
    async def test_create_applet_single_multi_select_response_values_value_null_auto_set_value(
        self, client, applet_minimal_data, tom, response_type
    ) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
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
        assert resp.status_code == 201
        item = resp.json()["result"]["activities"][0]["items"][0]
        # We can use enumerate because we have 2 options and values should be
        # 0 and 1
        for i, o in enumerate(item["responseValues"]["options"]):
            assert o["value"] == i

    async def test_create_applet_single_select_rows_response_values_add_alerts_no_datamatrix(
        self, client, applet_minimal_data, single_select_row_response_values, single_select_row_config, tom
    ) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = applet_minimal_data.dict()
        single_select_row_config_data = single_select_row_config.dict()
        single_select_row_response_values_data = single_select_row_response_values.dict()
        single_select_row_config_data["set_alerts"] = True
        single_select_row_response_values_data["data_matrix"] = None
        item = data["activities"][0]["items"][0]
        item["config"] = single_select_row_config_data
        item["response_type"] = ResponseType.SINGLESELECTROWS
        item["response_values"] = single_select_row_response_values_data
        resp = await client.post(
            self.applet_create_url.format(owner_id=tom.id),
            data=data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == activity_errors.DataMatrixRequiredError.message

    async def test_create_applet_flow_wrong_activity_key(self, client, applet_minimal_data, tom) -> None:
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
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
        assert resp.status_code == 201

    async def test_update_applet_duplicated_activity_item_name_is_not_allowed(
        self, client, applet_minimal_data, tom, applet_one
    ):
        await client.login(self.login_url, tom.email_encrypted, "Test1234!")
        data = AppletUpdate(**applet_minimal_data.dict(exclude_unset=True)).dict()
        item = copy.deepcopy(data["activities"][0]["items"][0])
        data["activities"][0]["items"].append(item)
        resp = await client.put(
            self.applet_detail_url.format(pk=applet_one.id),
            data=data,
        )
        assert resp.status_code == 422
        result = resp.json()["result"]
        assert len(result) == 1
        assert result[0]["message"] == activity_errors.DuplicateActivityItemNameNameError.message
