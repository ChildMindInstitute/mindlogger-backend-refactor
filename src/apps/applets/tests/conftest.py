import uuid

import pytest

from apps.activities.domain.response_type_config import ResponseType


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
