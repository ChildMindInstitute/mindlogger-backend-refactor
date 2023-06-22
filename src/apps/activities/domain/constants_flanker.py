from apps.shared.domain import PublicModel

ORDER_BLOCK: list[str] = [
    "left-con",
    "right-con",
    "left-inc",
    "right-inc",
    "left-neut",
    "right-neut",
]


class TrialSettings(PublicModel):
    name: str
    property: str
    value: int


class BlockSettings(PublicModel):
    name: str
    order: list[str] = ORDER_BLOCK
    value: int


class ButtonSetting(PublicModel):
    name: str
    value: int


FLANKER_BUTTONS: list[ButtonSetting] = [
    ButtonSetting(
        name="<",
        value=0,
    ),
    ButtonSetting(
        name=">",
        value=1,
    ),
]


FLANKER_TRAILS: list[TrialSettings] = [
    TrialSettings(
        name="left-con",
        property="<<<<<",
        value=0,
    ),
    TrialSettings(
        name="right-inc",
        property="<<><<",
        value=1,
    ),
    TrialSettings(
        name="left-inc",
        property=">><>>",
        value=0,
    ),
    TrialSettings(
        name="right-con",
        property=">>>>>",
        value=1,
    ),
    TrialSettings(
        name="left-neut",
        property="--<--",
        value=0,
    ),
    TrialSettings(
        name="right-neut",
        property="-->--",
        value=1,
    ),
]


def build_flanker_bloks(number_of_blocks: int):
    return [
        BlockSettings(
            name=f"Block {count + 1}",
            value=count,
        )
        for count in range(number_of_blocks)
    ]


FLANKER_PRACTISE_BLOCKS: list[BlockSettings] = build_flanker_bloks(20)
FLANKER_TEST_BLOCKS: list[BlockSettings] = build_flanker_bloks(5)


class FlankerBaseConfig(PublicModel):
    trials: list[TrialSettings] = FLANKER_TRAILS
    buttons: list[ButtonSetting] = FLANKER_BUTTONS
    show_fixation: bool = True
    show_feedback: bool = True
    show_results: bool = True
    sampling_method: str = "randomize-order"
    next_button: str = "OK"
    sample_size: int = 1
    trial_duration: int = 3000
    fixation_duration: int = 500
    fixation_screen: str = "-----"
    minimum_accuracy: int = 75
    max_retry_count: int = 3
