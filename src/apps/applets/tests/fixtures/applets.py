import uuid

import pytest

from apps.activities.domain.activity_create import ActivityCreate
from apps.activities.domain.response_type_config import ResponseType
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.base import Encryption
from apps.applets.tests import constants


@pytest.fixture(scope="session")
def encryption() -> Encryption:
    return Encryption(
        public_key=str(constants.TEST_PUBLIC_KEY),
        prime=str(constants.TEST_PRIME),
        base=str(constants.TEST_BASE),
        # Account id is not used co can be random uuid
        account_id=str(uuid.uuid4()),
    )


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
                response_type=ResponseType.FLANKER,
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
def applet_minimal_data(encryption: Encryption, activity_create: ActivityCreate) -> AppletCreate:
    return AppletCreate(
        display_name="minimal required data to create applet",
        encryption=encryption,
        activities=[activity_create],
        activity_flows=[],
        link=None,
        require_login=False,
        pinned_at=None,
        retention_period=None,
        retention_type=None,
        stream_enabled=False,
        stream_ip_address=None,
        stream_port=None,
    )
