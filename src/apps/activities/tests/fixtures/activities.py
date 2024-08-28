import uuid

import pytest

from apps.activities.domain.activity_create import ActivityCreate, ActivityItemCreate
from apps.activities.domain.response_type_config import (
    ABTrailsConfig,
    ABTrailsDeviceType,
    ABTrailsOrder,
    BlockConfiguration,
    BlockType,
    ButtonConfiguration,
    FlankerConfig,
    InputType,
    MessageConfig,
    Phase,
    ResponseType,
    SamplingMethod,
    StabilityTrackerConfig,
    StimulusConfigId,
    StimulusConfiguration,
    UnityConfig,
)
from apps.shared.enums import Language


@pytest.fixture
def activity_create() -> ActivityCreate:
    return ActivityCreate(name="test", description={Language.ENGLISH: "test"}, items=[], key=uuid.uuid4())


@pytest.fixture
def activity_ab_trails_ipad_create() -> ActivityCreate:
    # All values are hardcoded on UI side. The 'key' field is random uuid
    return ActivityCreate(
        name="A/B Trails iPad",
        description={Language.ENGLISH: "A/B Trails"},
        is_hidden=False,
        report_included_item_name="",
        key=uuid.uuid4(),
        items=[
            ActivityItemCreate(
                question={"en": "Sample A"},
                response_type=ResponseType.ABTRAILS,
                response_values=None,
                config=ABTrailsConfig(
                    device_type=ABTrailsDeviceType.TABLET, order_name=ABTrailsOrder.FIRST, type=ResponseType.ABTRAILS
                ),
                name="ABTrails_tablet_1",
            ),
            ActivityItemCreate(
                question={"en": "Test A"},
                response_type=ResponseType.ABTRAILS,
                response_values=None,
                config=ABTrailsConfig(
                    device_type=ABTrailsDeviceType.TABLET, order_name=ABTrailsOrder.SECOND, type=ResponseType.ABTRAILS
                ),
                name="ABTrails_tablet_2",
            ),
            ActivityItemCreate(
                question={"en": "Sample B"},
                response_type=ResponseType.ABTRAILS,
                response_values=None,
                config=ABTrailsConfig(
                    device_type=ABTrailsDeviceType.TABLET, order_name=ABTrailsOrder.THIRD, type=ResponseType.ABTRAILS
                ),
                name="ABTrails_tablet_3",
            ),
            ActivityItemCreate(
                question={"en": "Test B"},
                response_type=ResponseType.ABTRAILS,
                response_values=None,
                config=ABTrailsConfig(
                    device_type=ABTrailsDeviceType.TABLET, order_name=ABTrailsOrder.FOURTH, type=ResponseType.ABTRAILS
                ),
                name="ABTrails_tablet_4",
            ),
        ],
    )


@pytest.fixture
def activity_ab_trails_mobile_create() -> ActivityCreate:
    # All values are hardcoded on UI side. The 'key' field is random uuid
    return ActivityCreate(
        name="A/B Trails Mobile",
        description={Language.ENGLISH: "A/B Trails"},
        is_hidden=False,
        report_included_item_name="",
        key=uuid.uuid4(),
        items=[
            ActivityItemCreate(
                question={"en": "Sample A"},
                response_type=ResponseType.ABTRAILS,
                response_values=None,
                config=ABTrailsConfig(
                    device_type=ABTrailsDeviceType.MOBILE, order_name=ABTrailsOrder.FIRST, type=ResponseType.ABTRAILS
                ),
                name="ABTrails_mobile_1",
                is_hidden=False,
            ),
            ActivityItemCreate(
                question={"en": "Test A"},
                response_type=ResponseType.ABTRAILS,
                response_values=None,
                config=ABTrailsConfig(
                    device_type=ABTrailsDeviceType.MOBILE, order_name=ABTrailsOrder.SECOND, type=ResponseType.ABTRAILS
                ),
                name="ABTrails_mobile_2",
                is_hidden=False,
            ),
            ActivityItemCreate(
                question={"en": "Sample B"},
                response_type=ResponseType.ABTRAILS,
                response_values=None,
                config=ABTrailsConfig(
                    device_type=ABTrailsDeviceType.MOBILE, order_name=ABTrailsOrder.THIRD, type=ResponseType.ABTRAILS
                ),
                name="ABTrails_mobile_3",
                is_hidden=False,
            ),
            ActivityItemCreate(
                question={"en": "Test B"},
                response_type=ResponseType.ABTRAILS,
                response_values=None,
                config=ABTrailsConfig(
                    device_type=ABTrailsDeviceType.MOBILE, order_name=ABTrailsOrder.FOURTH, type=ResponseType.ABTRAILS
                ),
                name="ABTrails_mobile_4",
                is_hidden=False,
            ),
        ],
    )


@pytest.fixture
def activity_flanker_create(remote_image: str, local_image_name: str) -> ActivityCreate:
    stimulus_id = uuid.uuid4()
    return ActivityCreate(
        name="Simple & Choice Reaction Time Task Builder",
        description={Language.ENGLISH: "description"},
        is_hidden=False,
        report_included_item_name="",
        is_performance_task=False,
        key=uuid.uuid4(),
        items=[
            ActivityItemCreate(
                question={"en": "description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Flanker_VSR_instructions",
                is_hidden=False,
            ),
            ActivityItemCreate(
                question={"en": "description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Flanker_Practice_instructions_1",
                is_hidden=False,
            ),
            ActivityItemCreate(
                question={"en": ""},
                response_type=ResponseType.FLANKER,
                response_values=None,
                config=FlankerConfig(
                    type=ResponseType.FLANKER,
                    stimulus_trials=[
                        StimulusConfiguration(
                            id=StimulusConfigId(str(stimulus_id)),
                            image=remote_image,
                            text=local_image_name,
                            value=0,
                        )
                    ],
                    blocks=[
                        BlockConfiguration(name="Block 1", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 2", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 3", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 4", order=[StimulusConfigId(str(stimulus_id))]),
                    ],
                    buttons=[
                        ButtonConfiguration(text="", image=remote_image, value=0),
                        ButtonConfiguration(text="", image=remote_image, value=1),
                    ],
                    next_button="OK",
                    fixation_duration=None,
                    fixation_screen=None,
                    minimum_accuracy=75,
                    sample_size=1,
                    sampling_method=SamplingMethod.RANDOMIZE_ORDER,
                    show_feedback=True,
                    show_fixation=False,
                    show_results=True,
                    trial_duration=3000,
                    is_last_practice=False,
                    is_first_practice=True,
                    is_last_test=False,
                    block_type=BlockType.PRACTICE,
                ),
                name="Flanker_Practice_1",
            ),
            ActivityItemCreate(
                question={"en": "description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Flanker_Practice_instructions_2",
                is_hidden=False,
            ),
            ActivityItemCreate(
                question={"en": ""},
                response_type=ResponseType.FLANKER,
                response_values=None,
                config=FlankerConfig(
                    type=ResponseType.FLANKER,
                    stimulus_trials=[
                        StimulusConfiguration(
                            id=StimulusConfigId(str(stimulus_id)),
                            image=remote_image,
                            text=local_image_name,
                            value=0,
                        )
                    ],
                    blocks=[
                        BlockConfiguration(name="Block 1", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 2", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 3", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 4", order=[StimulusConfigId(str(stimulus_id))]),
                    ],
                    buttons=[
                        ButtonConfiguration(
                            text="",
                            image=remote_image,
                            value=0,
                        ),
                        ButtonConfiguration(
                            text="",
                            image=remote_image,
                            value=1,
                        ),
                    ],
                    next_button="OK",
                    fixation_duration=None,
                    fixation_screen=None,
                    minimum_accuracy=75,
                    sample_size=1,
                    sampling_method=SamplingMethod.RANDOMIZE_ORDER,
                    show_feedback=True,
                    show_fixation=False,
                    show_results=True,
                    trial_duration=3000,
                    is_last_practice=False,
                    is_first_practice=False,
                    is_last_test=False,
                    block_type=BlockType.PRACTICE,
                ),
                name="Flanker_Practice_2",
            ),
            ActivityItemCreate(
                question={"en": "description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Flanker_Practice_instructions_3",
            ),
            ActivityItemCreate(
                question={"en": ""},
                response_type=ResponseType.FLANKER,
                response_values=None,
                config=FlankerConfig(
                    type=ResponseType.FLANKER,
                    stimulus_trials=[
                        StimulusConfiguration(
                            id=StimulusConfigId(str(stimulus_id)),
                            image=remote_image,
                            text=local_image_name,
                            value=0,
                        )
                    ],
                    blocks=[
                        BlockConfiguration(name="Block 1", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 2", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 3", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 4", order=[StimulusConfigId(str(stimulus_id))]),
                    ],
                    buttons=[
                        ButtonConfiguration(
                            text="",
                            image=remote_image,
                            value=0,
                        ),
                        ButtonConfiguration(
                            text="",
                            image=remote_image,
                            value=1,
                        ),
                    ],
                    next_button="OK",
                    fixation_duration=None,
                    fixation_screen=None,
                    minimum_accuracy=75,
                    sample_size=1,
                    sampling_method=SamplingMethod.RANDOMIZE_ORDER,
                    show_feedback=True,
                    show_fixation=False,
                    show_results=True,
                    trial_duration=3000,
                    is_last_practice=True,
                    is_first_practice=False,
                    is_last_test=False,
                    block_type=BlockType.PRACTICE,
                ),
                name="Flanker_Practice_3",
            ),
            ActivityItemCreate(
                question={"en": "description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Flanker_test_instructions_1",
            ),
            ActivityItemCreate(
                question={"en": ""},
                response_type=ResponseType.FLANKER,
                response_values=None,
                config=FlankerConfig(
                    type=ResponseType.FLANKER,
                    stimulus_trials=[
                        StimulusConfiguration(
                            id=StimulusConfigId(str(stimulus_id)),
                            image=remote_image,
                            text=local_image_name,
                            value=0,
                        )
                    ],
                    blocks=[
                        BlockConfiguration(name="Block 1", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 2", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 3", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 4", order=[StimulusConfigId(str(stimulus_id))]),
                    ],
                    buttons=[
                        ButtonConfiguration(
                            text="",
                            image=remote_image,
                            value=0,
                        ),
                        ButtonConfiguration(
                            text="",
                            image=remote_image,
                            value=1,
                        ),
                    ],
                    next_button="Continue",
                    fixation_duration=None,
                    fixation_screen=None,
                    minimum_accuracy=None,
                    sample_size=1,
                    sampling_method=SamplingMethod.RANDOMIZE_ORDER,
                    show_feedback=False,
                    show_fixation=False,
                    show_results=True,
                    trial_duration=3000,
                    is_last_practice=False,
                    is_first_practice=False,
                    is_last_test=False,
                    block_type=BlockType.TEST,
                ),
                name="Flanker_test_1",
            ),
            ActivityItemCreate(
                question={"en": "description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Flanker_test_instructions_2",
            ),
            ActivityItemCreate(
                question={"en": ""},
                response_type=ResponseType.FLANKER,
                response_values=None,
                config=FlankerConfig(
                    type=ResponseType.FLANKER,
                    stimulus_trials=[
                        StimulusConfiguration(
                            id=StimulusConfigId(str(stimulus_id)),
                            image=remote_image,
                            text=local_image_name,
                            value=0,
                            weight=None,
                        )
                    ],
                    blocks=[
                        BlockConfiguration(name="Block 1", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 2", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 3", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 4", order=[StimulusConfigId(str(stimulus_id))]),
                    ],
                    buttons=[
                        ButtonConfiguration(
                            text="",
                            image=remote_image,
                            value=0,
                        ),
                        ButtonConfiguration(
                            text="",
                            image=remote_image,
                            value=1,
                        ),
                    ],
                    next_button="Continue",
                    fixation_duration=None,
                    fixation_screen=None,
                    minimum_accuracy=None,
                    sample_size=1,
                    sampling_method=SamplingMethod.RANDOMIZE_ORDER,
                    show_feedback=False,
                    show_fixation=False,
                    show_results=True,
                    trial_duration=3000,
                    is_last_practice=False,
                    is_first_practice=False,
                    is_last_test=False,
                    block_type=BlockType.TEST,
                ),
                name="Flanker_test_2",
            ),
            ActivityItemCreate(
                question={"en": "description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Flanker_test_instructions_3",
            ),
            ActivityItemCreate(
                question={"en": ""},
                response_type=ResponseType.FLANKER,
                response_values=None,
                config=FlankerConfig(
                    type=ResponseType.FLANKER,
                    stimulus_trials=[
                        StimulusConfiguration(
                            id=StimulusConfigId(str(stimulus_id)),
                            image=remote_image,
                            text=local_image_name,
                            value=0,
                            weight=None,
                        )
                    ],
                    blocks=[
                        BlockConfiguration(name="Block 1", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 2", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 3", order=[StimulusConfigId(str(stimulus_id))]),
                        BlockConfiguration(name="Block 4", order=[StimulusConfigId(str(stimulus_id))]),
                    ],
                    buttons=[
                        ButtonConfiguration(
                            text="",
                            image=remote_image,
                            value=0,
                        ),
                        ButtonConfiguration(
                            text="",
                            image=remote_image,
                            value=1,
                        ),
                    ],
                    next_button="Finish",
                    fixation_duration=None,
                    fixation_screen=None,
                    minimum_accuracy=None,
                    sample_size=1,
                    sampling_method=SamplingMethod.RANDOMIZE_ORDER,
                    show_feedback=False,
                    show_fixation=False,
                    show_results=True,
                    trial_duration=3000,
                    is_last_practice=False,
                    is_first_practice=False,
                    is_last_test=True,
                    block_type=BlockType.TEST,
                ),
                name="Flanker_test_3",
            ),
        ],
    )


@pytest.fixture
def actvitiy_cst_gyroscope_create() -> ActivityCreate:
    return ActivityCreate(
        name="CST Gyroscope",
        description={Language.ENGLISH: "description"},
        is_hidden=False,
        report_included_item_name="",
        key=uuid.uuid4(),
        items=[
            ActivityItemCreate(
                question={"en": "description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Gyroscope_General_instruction",
            ),
            ActivityItemCreate(
                question={"en": "description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Gyroscope_Calibration_Practice_instruction",
            ),
            ActivityItemCreate(
                question={"en": ""},
                response_type=ResponseType.STABILITYTRACKER,
                response_values=None,
                config=StabilityTrackerConfig(
                    user_input_type=InputType.GYROSCOPE,
                    phase=Phase.PRACTICE,
                    trials_number=3,
                    duration_minutes=5.0,
                    lambda_slope=20.0,
                    type=ResponseType.STABILITYTRACKER,
                ),
                name="Gyroscope_Calibration_Practice",
            ),
            ActivityItemCreate(
                question={"en": "description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Gyroscope_Test_instruction",
            ),
            ActivityItemCreate(
                question={"en": ""},
                response_type=ResponseType.STABILITYTRACKER,
                response_values=None,
                config=StabilityTrackerConfig(
                    user_input_type=InputType.GYROSCOPE,
                    phase=Phase.TEST,
                    trials_number=3,
                    duration_minutes=5.0,
                    lambda_slope=20.0,
                    type=ResponseType.STABILITYTRACKER,
                ),
                name="Gyroscope_Test",
            ),
        ],
    )


@pytest.fixture
def actvitiy_cst_touch_create() -> ActivityCreate:
    return ActivityCreate(
        name="CST Touch",
        description={Language.ENGLISH: "description"},
        is_hidden=False,
        report_included_item_name="",
        key=uuid.uuid4(),
        items=[
            ActivityItemCreate(
                question={"en": "description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Touch_General_instruction",
            ),
            ActivityItemCreate(
                question={"en": "Description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Touch_Calibration_Practice_instruction",
            ),
            ActivityItemCreate(
                question={"en": ""},
                response_type=ResponseType.STABILITYTRACKER,
                response_values=None,
                config=StabilityTrackerConfig(
                    user_input_type=InputType.TOUCH,
                    phase=Phase.PRACTICE,
                    trials_number=3,
                    duration_minutes=5.0,
                    lambda_slope=20.0,
                    type=ResponseType.STABILITYTRACKER,
                ),
                name="Touch_Calibration_Practice",
            ),
            ActivityItemCreate(
                question={"en": "Description"},
                response_type=ResponseType.MESSAGE,
                response_values=None,
                config=MessageConfig(remove_back_button=True, timer=None, type=ResponseType.MESSAGE),
                name="Touch_Test_instruction",
            ),
            ActivityItemCreate(
                question={"en": ""},
                response_type=ResponseType.STABILITYTRACKER,
                response_values=None,
                config=StabilityTrackerConfig(
                    user_input_type=InputType.TOUCH,
                    phase=Phase.TEST,
                    trials_number=3,
                    duration_minutes=5.0,
                    lambda_slope=20.0,
                    type=ResponseType.STABILITYTRACKER,
                ),
                name="Touch_Test",
            ),
        ],
    )


@pytest.fixture
def activity_unity_create() -> ActivityCreate:
    return ActivityCreate(
        name="Unity",
        description={Language.ENGLISH: "Unity"},
        is_hidden=False,
        report_included_item_name="",
        key=uuid.uuid4(),
        items=[
            ActivityItemCreate(
                question={"en": "File"},
                response_type=ResponseType.UNITY,
                response_values=None,
                config=UnityConfig(),
                name="Unity_Item",
                is_hidden=False,
            ),
        ],
    )

