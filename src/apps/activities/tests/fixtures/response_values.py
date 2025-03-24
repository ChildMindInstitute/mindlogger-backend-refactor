import uuid
from typing import List, cast

import pytest

from apps.activities.domain.response_type_config import ResponseType
from apps.activities.domain.response_values import (
    AudioPlayerValues,
    AudioValues,
    DrawingProportion,
    DrawingValues,
    MultiSelectionRowsValues,
    MultiSelectionValues,
    NumberSelectionValues,
    ParagraphTextValues,
    PhrasalTemplateDisplayMode,
    PhrasalTemplateField,
    PhrasalTemplatePhrase,
    PhrasalTemplateValues,
    RequestHealthRecordDataOption,
    RequestHealthRecordDataOptType,
    RequestHealthRecordDataValues,
    SingleSelectionRowsValues,
    SingleSelectionValues,
    SliderRowsValue,
    SliderRowsValues,
    SliderValueAlert,
    SliderValues,
    _PhrasalTemplateItemResponseField,
    _PhrasalTemplateLineBreakField,
    _PhrasalTemplateSentenceField,
    _SingleSelectionDataOption,
    _SingleSelectionDataRow,
    _SingleSelectionOption,
    _SingleSelectionRow,
    _SingleSelectionValue,
)


@pytest.fixture
def single_select_response_values() -> SingleSelectionValues:
    return SingleSelectionValues(
        palette_name=None,
        options=[
            _SingleSelectionValue(
                id=str(uuid.uuid4()),
                text="text",
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


@pytest.fixture
def paragraph_response_values() -> ParagraphTextValues:
    return ParagraphTextValues(
        type=ResponseType.PARAGRAPHTEXT,
    )


@pytest.fixture
def multi_select_response_values(
    single_select_response_values: SingleSelectionValues,
) -> MultiSelectionValues:
    data = single_select_response_values.dict()
    data["type"] = ResponseType.MULTISELECT
    return MultiSelectionValues(**data)


@pytest.fixture
def slider_value_alert() -> SliderValueAlert:
    return SliderValueAlert(value=0, min_value=None, max_value=None, alert="alert")


@pytest.fixture
def slider_response_values() -> SliderValues:
    return SliderValues(
        min_label=None,
        max_label=None,
        scores=None,
        alerts=None,
        type=ResponseType.SLIDER,
    )


@pytest.fixture
def number_selection_response_values() -> NumberSelectionValues:
    return NumberSelectionValues(type=ResponseType.NUMBERSELECT)


@pytest.fixture
def drawing_response_values(remote_image: str) -> DrawingValues:
    return DrawingValues(
        drawing_background=remote_image,
        drawing_example=remote_image,
        type=ResponseType.DRAWING,
        proportion=DrawingProportion(enabled=True),
    )


@pytest.fixture
def slider_rows_response_values() -> SliderRowsValues:
    return SliderRowsValues(
        rows=[
            SliderRowsValue(
                id=str(uuid.uuid4()),
                min_label=None,
                max_label=None,
                label="label",
            )
        ],
        type=ResponseType.SLIDERROWS,
    )


@pytest.fixture
def single_select_row_option() -> _SingleSelectionOption:
    return _SingleSelectionOption(id=str(uuid.uuid4()), text="text")


@pytest.fixture
def single_select_row() -> _SingleSelectionRow:
    return _SingleSelectionRow(id=str(uuid.uuid4()), row_name="row_name")


@pytest.fixture
def signle_select_row_data_option(
    single_select_row_option: _SingleSelectionOption,
) -> _SingleSelectionDataOption:
    option_id = cast(str, single_select_row_option.id)
    return _SingleSelectionDataOption(option_id=option_id)


@pytest.fixture
def single_select_row_data_row(
    single_select_row: _SingleSelectionRow,
    signle_select_row_data_option: _SingleSelectionDataOption,
) -> _SingleSelectionDataRow:
    row_id = cast(str, single_select_row.id)
    return _SingleSelectionDataRow(row_id=row_id, options=[signle_select_row_data_option])


@pytest.fixture
def single_select_row_response_values(
    single_select_row_option: _SingleSelectionOption,
    single_select_row: _SingleSelectionRow,
    single_select_row_data_row: _SingleSelectionDataRow,
) -> SingleSelectionRowsValues:
    return SingleSelectionRowsValues(
        rows=[single_select_row],
        options=[single_select_row_option],
        data_matrix=[single_select_row_data_row],
        type=ResponseType.SINGLESELECTROWS,
    )


@pytest.fixture
def multi_select_row_response_values(
    single_select_row_response_values: SingleSelectionRowsValues,
) -> MultiSelectionRowsValues:
    data = single_select_row_response_values.dict()
    data["type"] = ResponseType.MULTISELECTROWS
    return MultiSelectionRowsValues(**data)


@pytest.fixture
def audio_response_values() -> AudioValues:
    return AudioValues(max_duration=1, type=ResponseType.AUDIO)


@pytest.fixture
def audio_player_response_values() -> AudioPlayerValues:
    # TODO: Add some audio file
    return AudioPlayerValues(file=None, type=ResponseType.AUDIOPLAYER)


@pytest.fixture()
def phrasal_template_with_text_response_fields(text_item_create) -> List[PhrasalTemplateField]:
    return [
        _PhrasalTemplateSentenceField(text="test sentence"),
        _PhrasalTemplateItemResponseField(
            item_name=text_item_create.name, display_mode=PhrasalTemplateDisplayMode.SENTENCE
        ),
        _PhrasalTemplateLineBreakField(),
        _PhrasalTemplateSentenceField(text="test sentence 2"),
    ]


@pytest.fixture
def phrasal_template_with_text_response_values(phrasal_template_with_text_response_fields) -> PhrasalTemplateValues:
    return PhrasalTemplateValues(
        phrases=[PhrasalTemplatePhrase(image=None, fields=phrasal_template_with_text_response_fields)],
        card_title="test card title",
        type=ResponseType.PHRASAL_TEMPLATE,
    )


@pytest.fixture()
def phrasal_template_with_time_response_fields(time_item_create) -> List[PhrasalTemplateField]:
    return [
        _PhrasalTemplateSentenceField(text="test sentence"),
        _PhrasalTemplateItemResponseField(
            item_name=time_item_create.name, display_mode=PhrasalTemplateDisplayMode.SENTENCE, item_index=0
        ),
    ]


@pytest.fixture
def phrasal_template_with_time_response_values(
    phrasal_template_with_time_response_fields,
) -> PhrasalTemplateValues:
    return PhrasalTemplateValues(
        phrases=[PhrasalTemplatePhrase(image=None, fields=phrasal_template_with_time_response_fields)],
        card_title="test card title",
        type=ResponseType.PHRASAL_TEMPLATE,
    )


@pytest.fixture()
def phrasal_template_with_slider_rows_response_fields(slider_rows_item_create) -> List[PhrasalTemplateField]:
    return [
        _PhrasalTemplateSentenceField(text="test sentence"),
        _PhrasalTemplateItemResponseField(
            item_name=slider_rows_item_create.name, display_mode=PhrasalTemplateDisplayMode.SENTENCE, item_index=0
        ),
        _PhrasalTemplateLineBreakField(),
        _PhrasalTemplateSentenceField(text="test sentence 2"),
    ]


@pytest.fixture()
def phrasal_template_wiht_paragraph_response_fields(paragraph_text_item_create) -> List[PhrasalTemplateField]:
    return [
        _PhrasalTemplateSentenceField(text="test sentence"),
        _PhrasalTemplateItemResponseField(
            item_name=paragraph_text_item_create.name, display_mode=PhrasalTemplateDisplayMode.SENTENCE, item_index=0
        ),
        _PhrasalTemplateLineBreakField(),
        _PhrasalTemplateSentenceField(text="test sentence 2"),
    ]


@pytest.fixture
def phrasal_template_with_slider_rows_response_values(
    phrasal_template_with_slider_rows_response_fields,
) -> PhrasalTemplateValues:
    return PhrasalTemplateValues(
        phrases=[PhrasalTemplatePhrase(image=None, fields=phrasal_template_with_slider_rows_response_fields)],
        card_title="test card title",
        type=ResponseType.PHRASAL_TEMPLATE,
    )


@pytest.fixture
def phrasal_template_with_paragraph_response_values(
    phrasal_template_wiht_paragraph_response_fields,
) -> PhrasalTemplateValues:
    return PhrasalTemplateValues(
        phrases=[PhrasalTemplatePhrase(image=None, fields=phrasal_template_wiht_paragraph_response_fields)],
        card_title="test paragraph card title",
        type=ResponseType.PHRASAL_TEMPLATE,
    )


@pytest.fixture
def request_health_record_data_response_values() -> RequestHealthRecordDataValues:
    opt_in_out_options = [
        RequestHealthRecordDataOption(
            id=RequestHealthRecordDataOptType.OPT_IN,
            label="Opt In label",
        ),
        RequestHealthRecordDataOption(
            id=RequestHealthRecordDataOptType.OPT_OUT,
            label="Opt Out label",
        ),
    ]

    return RequestHealthRecordDataValues(
        type=ResponseType.REQUEST_HEALTH_RECORD_DATA, opt_in_out_options=opt_in_out_options
    )
