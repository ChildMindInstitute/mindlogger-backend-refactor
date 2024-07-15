import pytest

from apps.activities.domain.activity_create import ActivityItemCreate
from apps.activities.domain.response_type_config import (
    AudioConfig,
    AudioPlayerConfig,
    DateConfig,
    DrawingConfig,
    GeolocationConfig,
    MessageConfig,
    MultiSelectionConfig,
    MultiSelectionRowsConfig,
    NumberSelectionConfig,
    PhotoConfig,
    PhrasalTemplateConfig,
    ResponseType,
    SingleSelectionConfig,
    SingleSelectionRowsConfig,
    SliderConfig,
    SliderRowsConfig,
    TextConfig,
    TimeConfig,
    TimeRangeConfig,
    VideoConfig,
)
from apps.activities.domain.response_values import (
    AudioPlayerValues,
    AudioValues,
    DrawingValues,
    MultiSelectionRowsValues,
    MultiSelectionValues,
    NumberSelectionValues,
    PhrasalTemplateValues,
    SingleSelectionRowsValues,
    SingleSelectionValues,
    SliderRowsValues,
    SliderValues,
)
from apps.activities.tests.utils import BaseItemData


@pytest.fixture
def base_item_data() -> BaseItemData:
    return BaseItemData()


@pytest.fixture
def single_select_item_create(
    base_item_data: BaseItemData,
    single_select_config: SingleSelectionConfig,
    single_select_response_values: SingleSelectionValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        response_type=ResponseType.SINGLESELECT,
        response_values=single_select_response_values,
        config=single_select_config,
        **base_item_data.dict(),
    )


@pytest.fixture
def multi_select_item_create(
    base_item_data: BaseItemData,
    multi_select_config: MultiSelectionConfig,
    multi_select_response_values: MultiSelectionValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        response_type=ResponseType.MULTISELECT,
        response_values=multi_select_response_values,
        config=multi_select_config,
        **base_item_data.dict(),
    )


@pytest.fixture
def slider_item_create(
    base_item_data: BaseItemData,
    slider_config: SliderConfig,
    slider_response_values: SliderValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        response_type=ResponseType.SLIDER,
        response_values=slider_response_values,
        config=slider_config,
        **base_item_data.dict(),
    )


@pytest.fixture
def date_item_create(date_config: DateConfig, base_item_data: BaseItemData) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.DATE,
        config=date_config,
    )


@pytest.fixture
def number_selection_item_create(
    number_selection_config: NumberSelectionConfig,
    number_selection_response_values: NumberSelectionValues,
    base_item_data: BaseItemData,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.NUMBERSELECT,
        config=number_selection_config,
        response_values=number_selection_response_values,
    )


@pytest.fixture
def time_item_create(time_config: TimeConfig, base_item_data: BaseItemData) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.TIME,
        config=time_config,
    )


@pytest.fixture
def time_range_item_create(time_range_config: TimeRangeConfig, base_item_data: BaseItemData) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.TIMERANGE,
        config=time_range_config,
    )


@pytest.fixture
def single_select_row_item_create(
    base_item_data: BaseItemData,
    single_select_row_config: SingleSelectionRowsConfig,
    single_select_row_response_values: SingleSelectionRowsValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        config=single_select_row_config,
        response_values=single_select_row_response_values,
        response_type=ResponseType.SINGLESELECTROWS,
    )


@pytest.fixture
def multi_select_row_item_create(
    base_item_data: BaseItemData,
    multi_select_row_config: MultiSelectionRowsConfig,
    multi_select_row_response_values: MultiSelectionRowsValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        config=multi_select_row_config,
        response_values=multi_select_row_response_values,
        response_type=ResponseType.MULTISELECTROWS,
    )


@pytest.fixture
def slider_rows_item_create(
    base_item_data: BaseItemData,
    slider_rows_config: SliderRowsConfig,
    slider_rows_response_values: SliderRowsValues,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.SLIDERROWS,
        response_values=slider_rows_response_values,
        config=slider_rows_config,
    )


@pytest.fixture
def text_item_create(text_config: TextConfig, base_item_data: BaseItemData) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.TEXT,
        config=text_config,
    )


@pytest.fixture
def drawing_item_create(
    drawing_config: DrawingConfig, drawing_response_values: DrawingValues, base_item_data: BaseItemData
) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.DRAWING,
        config=drawing_config,
        response_values=drawing_response_values,
    )


@pytest.fixture
def photo_item_create(photo_config: PhotoConfig, base_item_data: BaseItemData) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.PHOTO,
        config=photo_config,
    )


@pytest.fixture
def video_item_create(video_config: VideoConfig, base_item_data: BaseItemData) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.VIDEO,
        config=video_config,
    )


@pytest.fixture
def geolocation_item_create(geolocation_config: GeolocationConfig, base_item_data: BaseItemData) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.GEOLOCATION,
        config=geolocation_config,
    )


@pytest.fixture
def audio_item_create(
    audio_config: AudioConfig, audio_response_values: AudioValues, base_item_data: BaseItemData
) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.AUDIO,
        config=audio_config,
        response_values=audio_response_values,
    )


@pytest.fixture
def message_item_create(message_config: MessageConfig, base_item_data: BaseItemData) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.MESSAGE,
        config=message_config,
    )


@pytest.fixture
def audio_player_item_create(
    audio_player_config: AudioPlayerConfig,
    audio_player_response_values: AudioPlayerValues,
    base_item_data: BaseItemData,
) -> ActivityItemCreate:
    return ActivityItemCreate(
        **base_item_data.dict(),
        response_type=ResponseType.AUDIOPLAYER,
        config=audio_player_config,
        response_values=audio_player_response_values,
    )


@pytest.fixture()
def phrasal_template_with_text_create(
    phrasal_template_config: PhrasalTemplateConfig,
    phrasal_template_with_text_response_values: PhrasalTemplateValues,
    base_item_data: BaseItemData,
    text_item_create,
):
    phrasal_item = ActivityItemCreate(
        **base_item_data.dict(exclude={"name"}),
        name="phrasal_template_text_test",
        response_type=ResponseType.PHRASAL_TEMPLATE,
        config=phrasal_template_config,
        response_values=phrasal_template_with_text_response_values,
    )

    return [text_item_create, phrasal_item]


@pytest.fixture
def phrasal_template_with_slider_rows_create(
    phrasal_template_config: PhrasalTemplateConfig,
    phrasal_template_with_slider_rows_response_values: PhrasalTemplateValues,
    base_item_data: BaseItemData,
    slider_rows_item_create,
):
    phrasal_item = ActivityItemCreate(
        **base_item_data.dict(exclude={"name"}),
        name="phrasal_template_slider_test",
        response_type=ResponseType.PHRASAL_TEMPLATE,
        config=phrasal_template_config,
        response_values=phrasal_template_with_slider_rows_response_values,
    )

    return [slider_rows_item_create, phrasal_item]
