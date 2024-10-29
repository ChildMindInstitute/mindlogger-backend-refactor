import uuid

from apps.activities.domain.activity_create import ActivityItemCreate
from apps.activities.domain.response_type_config import AdditionalResponseOption, ResponseType, SingleSelectionConfig
from apps.activities.domain.response_values import SingleSelectionValues, _SingleSelectionValue


def build_single_select_activity_item(
    name: str, text: str = "Single select activity item text", question: str = "Single select activity item question"
) -> ActivityItemCreate:
    response_values = SingleSelectionValues(
        palette_name=None,
        options=[
            _SingleSelectionValue(
                id=str(uuid.uuid4()),
                text=text,
                image=None,
                score=None,
                tooltip=None,
                is_hidden=False,
                color=None,
                value=0,
            )
        ],
        type=ResponseType.SINGLESELECT,
    )

    config = SingleSelectionConfig(
        randomize_options=False,
        timer=0,
        add_scores=False,
        add_tokens=False,
        set_alerts=False,
        add_tooltip=False,
        set_palette=False,
        remove_back_button=False,
        skippable_item=False,
        additional_response_option=AdditionalResponseOption(text_input_option=False, text_input_required=False),
        type=ResponseType.SINGLESELECT,
    )

    activity_item = ActivityItemCreate(
        response_type=ResponseType.SINGLESELECT,
        response_values=response_values,
        config=config,
        question={"en": question},
        name=name,
    )

    return activity_item
