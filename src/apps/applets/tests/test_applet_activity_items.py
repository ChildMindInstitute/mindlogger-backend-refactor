import copy
import uuid

import pytest

from apps.activities import errors as activity_errors
from apps.activities.domain.response_type_config import (
    ResponseType,
    SingleSelectionConfig,
)
from apps.activities.domain.response_values import SingleSelectionValues
from apps.shared.test import BaseTest
from infrastructure.database import rollback


@pytest.fixture
def activity_flanker_data():
    return dict(
        name="Activity_flanker",
        key="577dbbda-3afc-4962-842b-8d8d11588bfe",
        description=dict(
            en="Description Activity flanker.",
            fr="Description Activity flanker.",
        ),
        items=[
            dict(
                name="Flanker_VSR_instructionsn",
                # Nobody knows for what we need so big description
                question=dict(
                    en="## General Instructions\n\n\n You will "
                    "see arrows presented at the center of the "
                    "screen that point either to the left ‘<’ "
                    "or right ‘>’.\n Press the left button "
                    "if the arrow is pointing to the left ‘<’ "
                    "or press the right button if the arrow is "
                    "pointing to the right ‘>’.\n These arrows "
                    "will appear in the center of a line of "
                    "other items. Sometimes, these other items "
                    "will be arrows pointing in the same "
                    "direction, e.g.. ‘> > > > >’, or in the "
                    "opposite direction, e.g. ‘< < > < <’.\n "
                    "Your job is to respond to the central "
                    "arrow, no matter what direction the other "
                    "arrows are pointing.\n For example, you "
                    "would press the left button for both "
                    "‘< < < < <’, and ‘> > < > >’ because the "
                    "middle arrow points to the left.\n "
                    "Finally, in some trials dashes ‘ - ’ "
                    "will appear beside the central arrow.\n "
                    "Again, respond only to the direction "
                    "of the central arrow. Please respond "
                    "as quickly and accurately as possible.",
                    fr="Flanker General instruction text.",
                ),
                response_type="message",
                response_values=None,
                config=dict(
                    remove_back_button=False,
                    timer=None,
                ),
            ),
            dict(
                name="Flanker_Practice_instructions_1",
                question=dict(
                    en="## Instructions\n\nNow you will have a "
                    "chance to practice the task before moving "
                    "on to the test phase.\nRemember to "
                    "respond only to the central arrow\n",
                    fr="Flanker Сalibration/Practice " "instruction 1 text.",
                ),
                response_type="message",
                response_values=None,
                config=dict(
                    remove_back_button=False,
                    timer=None,
                ),
            ),
            dict(
                name="Flanker_Practise_1",
                question=dict(
                    en="Flanker_Practise_1",
                    fr="Flanker_Practise_1",
                ),
                response_type="flanker",
                response_values=None,
                config=dict(
                    stimulusTrials=[
                        {
                            "id": "1",
                            "image": "https://600.jpg",
                            "text": "left-con",
                            "value": 0,
                            "weight": 10,
                        },
                        {
                            "id": "2",
                            "image": "https://600.jpg",
                            "text": "right-inc",
                            "value": 1,
                            "weight": 10,
                        },
                        {
                            "id": "3",
                            "image": "https://600.jpg",
                            "text": "left-inc",
                            "value": 0,
                            "weight": 10,
                        },
                        {
                            "id": "4",
                            "image": "https://600.jpg",
                            "text": "right-con",
                            "value": 1,
                            "weight": 10,
                        },
                        {
                            "id": "5",
                            "image": "https://600.jpg",
                            "text": "left-neut",
                            "value": 0,
                            "weight": 10,
                        },
                        {
                            "id": "6",
                            "image": "https://600.jpg",
                            "text": "right-neut",
                            "value": 1,
                            "weight": 10,
                        },
                    ],
                    blocks=[
                        {
                            "name": "Block 1",
                            "order": [
                                "left-con",
                                "right-con",
                                "left-inc",
                                "right-inc",
                                "left-neut",
                                "right-neut",
                            ],
                        },
                        {
                            "name": "Block 2",
                            "order": [
                                "left-con",
                                "right-con",
                                "left-inc",
                                "right-inc",
                                "left-neut",
                                "right-neut",
                            ],
                        },
                    ],
                    buttons=[
                        {
                            "text": "Button_1_name_<",
                            "image": "https://1.jpg",
                            "value": 0,
                        },
                        {
                            "text": "Button_2_name_>",
                            "image": "https://2.jpg",
                            "value": 1,
                        },
                    ],
                    nextButton="OK",
                    fixationDuration=500,
                    fixationScreen={
                        "value": "FixationScreen_value",
                        "image": "https://fixation-screen.jpg",
                    },
                    minimumAccuracy=75,
                    sampleSize=1,
                    samplingMethod="randomize-order",
                    showFeedback=True,
                    showFixation=True,
                    showResults=False,
                    trialDuration=3000,
                    isLastPractice=False,
                    isFirstPractice=True,
                    isLastTest=False,
                    blockType="practice",
                ),
            ),
        ],
    )


@pytest.fixture
def single_select_response_values():
    return dict(
        options=[
            dict(
                id=uuid.uuid4(),
                text="text",
                image=None,
                score=None,
                tooltip=None,
                is_hidden=False,
                color=None,
                value=0,
            )
        ]
    )


@pytest.fixture
def single_select_config():
    return dict(
        randomize_options=False,
        timer=0,
        add_scores=False,
        set_alerts=False,
        add_tooltip=False,
        set_palette=False,
        remove_back_button=False,
        skippable_item=False,
        additional_response_option=dict(
            text_input_option=False,
            text_input_required=False,
        ),
    )


@pytest.fixture
def applet_minimal_data(single_select_response_values, single_select_config):
    return dict(
        display_name="minimal required data to create applet",
        encryption=dict(
            public_key=uuid.uuid4().hex,
            prime=uuid.uuid4().hex,
            base=uuid.uuid4().hex,
            account_id=str(uuid.uuid4()),
        ),
        description=dict(en="description"),
        activities=[
            dict(
                name="name",
                key=uuid.uuid4(),
                description=dict(en="description"),
                items=[
                    dict(
                        name="item1",
                        question=dict(en="question"),
                        response_type=ResponseType.SINGLESELECT,
                        response_values=single_select_response_values,
                        config=single_select_config,
                    ),
                ],
            )
        ],
        # Empty, but required
        activity_flows=[],
    )


@pytest.fixture
def slider_response_values():
    return dict(
        min_value=0,
        max_value=10,
        min_label="min_label",
        max_label="max_label",
        min_image=None,
        max_image=None,
        scores=None,
        alerts=None,
    )


@pytest.fixture
def slider_config():
    return dict(
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
    )


@pytest.fixture
def slider_rows_response_values():
    return dict(
        rows=[
            {
                "label": "label1",
                "min_label": "min_label1",
                "max_label": "max_label1",
                "min_value": 0,
                "max_value": 10,
                "min_image": None,
                "max_image": None,
                "scores": None,
                "alerts": None,
            }
        ]
    )


@pytest.fixture
def slider_rows_config():
    return dict(
        remove_back_button=False,
        skippable_item=False,
        add_scores=False,
        set_alerts=False,
        timer=1,
    )


@pytest.fixture
def single_select_rows_response_values():
    return dict(
        rows=[
            {
                "id": "17e69155-22cd-4484-8a49-364779ea9df1",
                "row_name": "row1",
                "row_image": None,
                "tooltip": None,
            },
        ],
        options=[
            {
                "id": "17e69155-22cd-4484-8a49-364779ea9de1",
                "text": "option1",
                "image": None,
                "tooltip": None,
            }
        ],
        data_matrix=[
            {
                "row_id": "17e69155-22cd-4484-8a49-364779ea9df1",
                "options": [
                    {
                        "option_id": "17e69155-22cd-4484-8a49-364779ea9de1",
                        "score": 1,
                        "alert": "alert1",
                    },
                ],
            },
            {
                "row_id": "17e69155-22cd-4484-8a49-364779ea9df2",
                "options": [
                    {
                        "option_id": "17e69155-22cd-4484-8a49-364779ea9de1",
                        "score": 3,
                        "alert": None,
                    },
                ],
            },
        ],
    )


@pytest.fixture
def single_select_rows_config():
    return dict(
        remove_back_button=False,
        skippable_item=False,
        add_scores=False,
        set_alerts=False,
        timer=1,
        add_tooltip=False,
    )


class TestActivityItems(BaseTest):
    fixtures = [
        "users/fixtures/users.json",
        "themes/fixtures/themes.json",
        "folders/fixtures/folders.json",
        "applets/fixtures/applets.json",
        "applets/fixtures/applet_histories.json",
        "applets/fixtures/applet_user_accesses.json",
        "activities/fixtures/activities.json",
        "activities/fixtures/activity_items.json",
        "activity_flows/fixtures/activity_flows.json",
        "activity_flows/fixtures/activity_flow_items.json",
    ]

    login_url = "/auth/login"
    applet_list_url = "applets"
    applet_create_url = "workspaces/{owner_id}/applets"
    applet_detail_url = f"{applet_list_url}/{{pk}}"
    activity_detail_url = "activities/{activity_id}"
    applet_workspace_detail_url = "workspaces/{owner_id}/applets/{pk}"

    @rollback
    async def test_creating_applet_with_activity_items(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
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
                                    {"text": "option2", "value": 1, "is_none_above": False}
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
                    items=[
                        dict(
                            activity_key="577dbbda-3afc-"
                            "4962-842b-8d8d11588bfe"
                        )
                    ],
                )
            ],
        )
        response = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.applet_detail_url.format(pk=response.json()["result"]["id"])
        )
        assert response.status_code == 200

    @rollback
    async def test_creating_applet_with_ab_trails_mobile_activity_items(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
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
                    items=[
                        dict(
                            activity_key="577dbbda-3afc-"
                            "4962-842b-8d8d11588bfe"
                        )
                    ],
                )
            ],
        )
        response = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.applet_detail_url.format(pk=response.json()["result"]["id"])
        )
        assert response.status_code == 200

    @rollback
    async def test_creating_applet_with_ab_trails_tablet_activity_items(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
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
                    items=[
                        dict(
                            activity_key="577dbbda-3afc-"
                            "4962-842b-8d8d11588bfe"
                        )
                    ],
                )
            ],
        )
        response = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.applet_detail_url.format(pk=response.json()["result"]["id"])
        )
        assert response.status_code == 200

    @rollback
    async def test_creating_applet_with_gyroscope_activity_items(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
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
                                en="Gyroscope Сalibration/Practice "
                                "instruction text.",
                                fr="Gyroscope Сalibration/Practice "
                                "instruction text.",
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
                    items=[
                        dict(
                            activity_key="577dbbda-3afc-"
                            "4962-842b-8d8d11588bfe"
                        )
                    ],
                )
            ],
        )
        response = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.applet_detail_url.format(pk=response.json()["result"]["id"])
        )
        assert response.status_code == 200

    @rollback
    async def test_creating_applet_with_touch_activity_items(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
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
                                en="Touch Сalibration/Practice "
                                "instruction text.",
                                fr="Touch Сalibration/Practice "
                                "instruction text.",
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
                    items=[
                        dict(
                            activity_key="577dbbda-3afc-"
                            "4962-842b-8d8d11588bfe"
                        )
                    ],
                )
            ],
        )
        response = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.applet_detail_url.format(pk=response.json()["result"]["id"])
        )
        assert response.status_code == 200

    @rollback
    async def test_creating_applet_with_activity_items_condition(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
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
                                                item_name=(
                                                    "activity_item_"
                                                    "singleselect_score"
                                                ),
                                                type="GREATER_THAN",
                                                payload=dict(
                                                    value=1,
                                                ),
                                            ),
                                            dict(
                                                item_name=(
                                                    "activity_item_"
                                                    "singleselect_score"
                                                ),
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
                                        item_name="activity_item_singleselect_2",  # noqa: E501
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
                                        item_name="activity_item_multiselect_2",  # noqa: E501
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
        response = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=create_data,
        )
        assert response.status_code == 400
        assert (
            response.json()["result"][0]["message"]
            == activity_errors.IncorrectConditionItemIndexError.message
        )

        text_item = create_data["activities"][0]["items"][1]
        slider_item_2 = create_data["activities"][0]["items"][6]
        create_data["activities"][0]["items"][1] = slider_item_2
        create_data["activities"][0]["items"][6] = text_item

        response = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=create_data,
        )
        assert response.status_code == 201, response.json()
        assert (
            type(
                response.json()["result"]["activities"][0]["items"][6][
                    "conditionalLogic"
                ]
            )
            == dict
        )
        assert (
            type(
                response.json()["result"]["activities"][0]["scoresAndReports"]
            )
            == dict
        )
        assert (
            type(response.json()["result"]["activities"][0]["subscaleSetting"])
            == dict
        )
        response = await self.client.get(
            self.applet_detail_url.format(pk=response.json()["result"]["id"])
        )
        assert response.status_code == 200

        activity_id = response.json()["result"]["activities"][0]["id"]
        response = await self.client.get(
            self.activity_detail_url.format(activity_id=activity_id)
        )
        assert response.status_code == 200
        assert (
            type(response.json()["result"]["items"][6]["conditionalLogic"])
            == dict
        )

    @rollback
    async def test_creating_activity_items_without_option_value(self):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
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
                    items=[
                        dict(
                            activity_key="577dbbda-3afc-"
                            "4962-842b-8d8d11588bfe"
                        )
                    ],
                )
            ],
        )
        response = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        response = await self.client.get(
            self.applet_detail_url.format(pk=response.json()["result"]["id"])
        )
        assert response.status_code == 200
        applet_id = response.json()["result"]["id"]

        response = await self.client.get(
            self.activity_detail_url.format(
                activity_id=response.json()["result"]["activities"][0]["id"]
            )
        )
        slider_rows_id = response.json()["result"]["items"][0]["id"]

        assert response.status_code == 200
        assert (
            response.json()["result"]["items"][3]["responseValues"]["options"][
                0
            ]["value"]
            == 0
        )

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

        response = await self.client.put(
            self.applet_detail_url.format(pk=applet_id),
            data=create_data,
        )
        assert response.status_code == 200

    @rollback
    async def test_create_applet_with_flanker_preformance_task(
        self, activity_flanker_data
    ):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

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

        response = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=create_data,
        )
        assert response.status_code == 201, response.json()

        assert response.json()["result"]["activities"][0]["isPerformanceTask"]
        assert (
            response.json()["result"]["activities"][0]["performanceTaskType"]
            == "flanker"
        )

        # Check that the 'get' after creating new applet returns correct data
        response = await self.client.get(
            self.applet_workspace_detail_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                pk=response.json()["result"]["id"],
            )
        )
        assert response.status_code == 200
        assert response.json()["result"]["activities"][0]["isPerformanceTask"]
        assert (
            response.json()["result"]["activities"][0]["performanceTaskType"]
            == "flanker"
        )

    @rollback
    async def test_applet_add_performance_task_to_the_applet(
        self, activity_flanker_data
    ):
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )

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

        response = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=create_data,
        )
        assert response.status_code == 201
        activity = response.json()["result"]["activities"][0]
        assert not activity["isPerformanceTask"]
        assert not activity["performanceTaskType"]
        # Test that get after creating new applet returns correct data
        # Generaly we don't need to test, tested data, but for now let leave
        # it here
        response = await self.client.get(
            self.applet_workspace_detail_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                pk=response.json()["result"]["id"],
            )
        )
        assert response.status_code == 200
        activity = response.json()["result"]["activities"][0]
        assert not activity["isPerformanceTask"]
        assert not activity["performanceTaskType"]

        # Add flanker performance task
        create_data["activities"].append(activity_flanker_data)

        response = await self.client.put(
            self.applet_detail_url.format(pk=response.json()["result"]["id"]),
            data=create_data,
        )
        assert response.status_code == 200
        flanker = response.json()["result"]["activities"][1]
        assert flanker["isPerformanceTask"]
        assert flanker["performanceTaskType"] == "flanker"

        # Check the 'get' method
        response = await self.client.get(
            self.applet_workspace_detail_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1",
                pk=response.json()["result"]["id"],
            )
        )
        assert response.status_code == 200
        flanker = response.json()["result"]["activities"][1]
        assert flanker["isPerformanceTask"]
        assert flanker["performanceTaskType"] == "flanker"

    @rollback
    async def test_create_applet_item_name_is_not_valid(
        self, applet_minimal_data
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        applet_minimal_data["activities"][0]["items"][0]["name"] = "%name"
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert (
            errors[0]["message"]
            == activity_errors.IncorrectNameCharactersError.message
        )

    @rollback
    async def test_create_applet_item_config_not_valid(
        self, applet_minimal_data
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        del applet_minimal_data["activities"][0]["items"][0]["config"][
            "add_scores"
        ]
        del applet_minimal_data["activities"][0]["items"][0]["config"][
            "set_alerts"
        ]
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0][
            "message"
        ] == activity_errors.IncorrectConfigError.message.format(
            type=SingleSelectionConfig
        )

    @rollback
    async def test_create_applet_not_valid_response_type(
        self, applet_minimal_data
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        applet_minimal_data["activities"][0]["items"][0][
            "response_type"
        ] = "NotValid"
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0][
            "message"
        ] == activity_errors.IncorrectResponseValueError.message.format(
            type=ResponseType
        )

    @rollback
    @pytest.mark.parametrize(
        "value,error_msg",
        (
            (
                {},
                activity_errors.IncorrectResponseValueError.message.format(
                    type=SingleSelectionValues
                ),
            ),
            (
                None,
                activity_errors.IncorrectResponseValueError.message.format(
                    type=SingleSelectionValues
                ),
            ),
        ),
    )
    async def test_create_applet_not_valid_response_values(  # noqa: E501
        self, applet_minimal_data, value, error_msg
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        applet_minimal_data["activities"][0]["items"][0][
            "response_values"
        ] = value
        applet_minimal_data["activities"][0]["items"][0][
            "response_type"
        ] = ResponseType.SINGLESELECT
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == error_msg

    @rollback
    async def test_create_applet_without_item_response_type(
        self, applet_minimal_data
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        del applet_minimal_data["activities"][0]["items"][0]["response_type"]
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == "field required"

    @rollback
    async def test_create_applet_single_select_add_scores_not_scores_in_response_values(  # noqa: E501
        self, applet_minimal_data
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        applet_minimal_data["activities"][0]["items"][0]["config"][
            "add_scores"
        ] = True
        applet_minimal_data["activities"][0]["items"][0][
            "response_type"
        ] = ResponseType.SINGLESELECT
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert (
            errors[0]["message"]
            == activity_errors.ScoreRequiredForResponseValueError.message
        )

    @rollback
    async def test_create_applet_slider_response_values_add_scores_not_scores_in_response_values(  # noqa: E501
        self, applet_minimal_data, slider_response_values, slider_config
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        slider_config["add_scores"] = True
        applet_minimal_data["activities"][0]["items"][0][
            "config"
        ] = slider_config
        applet_minimal_data["activities"][0]["items"][0][
            "response_type"
        ] = ResponseType.SLIDER
        applet_minimal_data["activities"][0]["items"][0][
            "response_values"
        ] = slider_response_values
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == activity_errors.NullScoreError.message

    @rollback
    async def test_create_applet_slider_response_values_add_scores_scores_not_for_all_values(  # noqa: E501
        self, applet_minimal_data, slider_response_values, slider_config
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        slider_config["add_scores"] = True
        min_val = slider_response_values["min_value"]
        max_val = slider_response_values["max_value"]
        scores = [i for i in range(max_val - min_val)]
        slider_response_values["scores"] = scores
        applet_minimal_data["activities"][0]["items"][0][
            "config"
        ] = slider_config
        applet_minimal_data["activities"][0]["items"][0][
            "response_type"
        ] = ResponseType.SLIDER
        applet_minimal_data["activities"][0]["items"][0][
            "response_values"
        ] = slider_response_values
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert (
            errors[0]["message"]
            == activity_errors.InvalidScoreLengthError.message
        )

    @rollback
    async def test_create_applet_slider_rows_response_values_add_scores_true_no_scores(  # noqa: E501
        self,
        applet_minimal_data,
        slider_rows_response_values,
        slider_rows_config,
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        slider_rows_config["add_scores"] = True
        slider_rows_response_values["rows"][0]["scores"] = None
        item = applet_minimal_data["activities"][0]["items"][0]
        item["config"] = slider_rows_config
        item["response_type"] = ResponseType.SLIDERROWS
        item["response_values"] = slider_rows_response_values
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert errors[0]["message"] == activity_errors.NullScoreError.message

    @rollback
    async def test_create_applet_slider_rows_response_values_add_scores_true_scores_not_for_all_values(  # noqa: E501
        self,
        applet_minimal_data,
        slider_rows_response_values,
        slider_rows_config,
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        slider_rows_config["add_scores"] = True
        min_val = slider_rows_response_values["rows"][0]["min_value"]
        max_val = slider_rows_response_values["rows"][0]["max_value"]
        slider_rows_response_values["rows"][0]["scores"] = [
            i for i in range(max_val - min_val)
        ]
        item = applet_minimal_data["activities"][0]["items"][0]
        item["config"] = slider_rows_config
        item["response_type"] = ResponseType.SLIDERROWS
        item["response_values"] = slider_rows_response_values
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert (
            errors[0]["message"]
            == activity_errors.InvalidScoreLengthError.message
        )

    @rollback
    @pytest.mark.parametrize(
        "response_type", (ResponseType.SINGLESELECT, ResponseType.MULTISELECT)
    )
    async def test_create_applet_single_multi_select_response_values_value_null_auto_set_value(  # noqa: E501
        self, applet_minimal_data, response_type
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        item = applet_minimal_data["activities"][0]["items"][0]
        option = item["response_values"]["options"][0]
        del option["value"]
        option2 = copy.deepcopy(option)
        option2["value"] = None
        item["response_values"]["options"].append(option2)
        item["response_type"] = response_type
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 201
        item = resp.json()["result"]["activities"][0]["items"][0]
        # We can use enumerate because we have 2 options and values should be
        # 0 and 1
        for i, o in enumerate(item["responseValues"]["options"]):
            assert o["value"] == i

    @rollback
    async def test_create_applet_single_select_rows_response_values_add_alerts_no_datamatrix(  # noqa: E501
        self,
        applet_minimal_data,
        single_select_rows_response_values,
        single_select_rows_config,
    ) -> None:
        await self.client.login(
            self.login_url, "tom@mindlogger.com", "Test1234!"
        )
        single_select_rows_config["set_alerts"] = True
        single_select_rows_response_values["data_matrix"] = None
        item = applet_minimal_data["activities"][0]["items"][0]
        item["config"] = single_select_rows_config
        item["response_type"] = ResponseType.SINGLESELECTROWS
        item["response_values"] = single_select_rows_response_values
        resp = await self.client.post(
            self.applet_create_url.format(
                owner_id="7484f34a-3acc-4ee6-8a94-fd7299502fa1"
            ),
            data=applet_minimal_data,
        )
        assert resp.status_code == 422
        errors = resp.json()["result"]
        assert len(errors) == 1
        assert (
            errors[0]["message"]
            == activity_errors.DataMatrixRequiredError.message
        )
