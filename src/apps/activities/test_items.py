from apps.activities.domain.response_type_config import (
    ResponseType,
    TextConfig,
    MessageConfig,
    NumberSelectionConfig,
    TimeRangeConfig,
    GeolocationConfig,
    PhotoConfig,
    VideoConfig,
    DateConfig,
    DrawingConfig,
    AudioConfig,
    AudioPlayerConfig,
    SliderRowsConfig,
    MultiSelectionRowsConfig,
    SingleSelectionRowsConfig,
    SingleSelectionConfig,
    MultiSelectionConfig,
    SliderConfig,
)

from apps.activities.domain.response_values import (
    TextValues,
    MessageValues,
    NumberSelectionValues,
    TimeRangeValues,
    GeolocationValues,
    PhotoValues,
    VideoValues,
    DateValues,
    DrawingValues,
    AudioValues,
    AudioPlayerValues,
    SliderRowsValues,
    MultiSelectionRowsValues,
    SingleSelectionRowsValues,
    SingleSelectionValues,
    MultiSelectionValues,
    SliderValues,
)

from apps.activities.domain.activity_item_base import BaseActivityItem


# text_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.TEXT,
#     response_values=TextValues(),
#     config=TextConfig(
#         max_response_length=300,
#         correct_answer_required=False,
#         correct_answer=None,
#         numerical_response_required=False,
#         response_data_identifier=False,
#         response_required=False,
#         remove_back_button=False,
#         skippable_item=False,
#     ),
#     name="text_item",
# )

# message_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.MESSAGE,
#     response_values=MessageValues(),
#     config=MessageConfig(
#         remove_back_button=False,
#         timer=1,
#     ),
#     name="message_item",
# )

# number_selection_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.NUMBERSELECT,
#     response_values=NumberSelectionValues(),
#     config=NumberSelectionConfig(
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#         remove_back_button=False,
#         skippable_item=False,
#     ),
#     name="number_selection_item",
# )

# time_range_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.TIMERANGE,
#     response_values=TimeRangeValues(),
#     config=TimeRangeConfig(
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#         remove_back_button=False,
#         skippable_item=False,
#         timer=1,
#     ),
#     name="time_range_item",
# )

# geolocation_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.GEOLOCATION,
#     response_values=GeolocationValues(),
#     config=GeolocationConfig(
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#         remove_back_button=False,
#         skippable_item=False,
#     ),
#     name="geolocation_item",
# )


# photo_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.PHOTO,
#     response_values=PhotoValues(),
#     config=PhotoConfig(
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#         remove_back_button=False,
#         skippable_item=False,
#     ),
#     name="photo_item",
# )

# video_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.VIDEO,
#     response_values=VideoValues(),
#     config=VideoConfig(
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#         remove_back_button=False,
#         skippable_item=False,
#     ),
#     name="video_item",
# )

# date_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.DATE,
#     response_values=DateValues(),
#     config=DateConfig(
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#         remove_back_button=False,
#         skippable_item=False,
#     ),
#     name="date_item",
# )

# drawing_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.DRAWING,
#     response_values=DrawingValues(
#         drawing_background="https://www.w3schools.com/css/img_5terre_wide.jpg",
#         drawing_example="https://www.w3schools.com/css/img_5terre_wide.jpg",
#     ),
#     config=DrawingConfig(
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#         remove_back_button=False,
#         skippable_item=False,
#         timer=1,
#         remove_undo_button=False,
#         navigation_to_top=False,
#     ),
#     name="drawing_item",
# )

# audio_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.AUDIO,
#     response_values=dict(max_duration=200),
#     config=dict(
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#         remove_back_button=False,
#         skippable_item=False,
#         timer=1,
#     ),
#     name="audio_item",
# )
# print(audio_item)

# audio_player_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.AUDIOPLAYER,
#     response_values=dict(
#         file="https://www.w3schools.com/html/horse.mp3",
#     ),
#     config=dict(
#         remove_back_button=False,
#         skippable_item=False,
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#         play_once=False,
#     ),
#     name="audio_player_item",
# )
# print(audio_player_item)

# print(audio_player_item)
# slider_rows_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.SLIDERROWS,
#     response_values=SliderRowsValues(
#         rows=[
#             {
#                 "label": "label1",
#                 "min_label": "min_label1",
#                 "max_label": "max_label1",
#                 "min_value": 0,
#                 "max_value": 10,
#                 "min_image": None,
#                 "max_image": None,
#                 "score": None,
#             }
#         ]
#     ),
#     config=SliderRowsConfig(
#         remove_back_button=False,
#         skippable_item=False,
#         add_scores=False,
#         set_alerts=False,
#         timer=1,
#     ),
#     name="slider_rows_item",
# )

# multi_row_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.MULTISELECTROWS,
#     response_values=MultiSelectionRowsValues(
#         rows=[
#             {
#                 "id": "17e69155-22cd-4484-8a49-364779ea9df1",
#                 "row_name": "row1",
#                 "row_image": None,
#                 "tooltip": None,
#             },
#             {
#                 "id": "17e69155-22cd-4484-8a49-364779ea9df2",
#                 "row_name": "row2",
#                 "row_image": None,
#                 "tooltip": None,
#             },
#         ],
#         options=[
#             {"text": "option1", "image": None, "tooltip": None},
#             {"text": "option2", "image": None, "tooltip": None},
#         ],
#         data_matrix=None,
#     ),
#     config=MultiSelectionRowsConfig(
#         remove_back_button=False,
#         skippable_item=False,
#         add_scores=False,
#         set_alerts=False,
#         timer=1,
#         add_tooltip=False,
#     ),
#     name="multi_row_item",
# )

# single_row_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.SINGLESELECTROWS,
#     response_values=SingleSelectionRowsValues(
#         rows=[
#             {
#                 "id": "17e69155-22cd-4484-8a49-364779ea9df1",
#                 "row_name": "row1",
#                 "row_image": None,
#                 "tooltip": None,
#             },
#             {
#                 "id": "17e69155-22cd-4484-8a49-364779ea9df2",
#                 "row_name": "row2",
#                 "row_image": None,
#                 "tooltip": None,
#             },
#         ],
#         options=[
#             {"text": "option1", "image": None, "tooltip": None},
#             {"text": "option2", "image": None, "tooltip": None},
#         ],
#         data_matrix=None,
#     ),
#     config=SingleSelectionRowsConfig(
#         remove_back_button=False,
#         skippable_item=False,
#         add_scores=False,
#         set_alerts=False,
#         timer=1,
#         add_tooltip=False,
#     ),
#     name="single_row_item",
# )

# single_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.SINGLESELECT,
#     response_values=SingleSelectionValues(
#         palette_name="palette1",
#         options=[
#             {"text": "option1"},
#             {"text": "option2"},
#         ],
#     ),
#     config=SingleSelectionConfig(
#         remove_back_button=False,
#         skippable_item=False,
#         add_scores=False,
#         set_alerts=False,
#         timer=1,
#         add_tooltip=False,
#         set_palette=False,
#         randomize_options=False,
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#     ),
#     name="single_item",
# )

# multi_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.MULTISELECT,
#     response_values=MultiSelectionValues(
#         palette_name="palette1",
#         options=[
#             {"text": "option1"},
#             {"text": "option2"},
#         ],
#     ),
#     config=MultiSelectionConfig(
#         remove_back_button=False,
#         skippable_item=False,
#         add_scores=False,
#         set_alerts=False,
#         timer=1,
#         add_tooltip=False,
#         set_palette=False,
#         randomize_options=False,
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#     ),
#     name="multi_item",
# )


# slider_item = BaseActivityItem(
#     question={"en": "What is your name?"},
#     response_type=ResponseType.SLIDER,
#     response_values=SliderValues(
#         min_value=0,
#         max_value=10,
#         min_label="min_label",
#         max_label="max_label",
#         min_image=None,
#         max_image=None,
#         scores=None,
#     ),
#     config=SliderConfig(
#         remove_back_button=False,
#         skippable_item=False,
#         add_scores=False,
#         set_alerts=False,
#         timer=1,
#         show_tick_labels=False,
#         show_tick_marks=False,
#         continuous_slider=False,
#         additional_response_option={
#             "text_input_option": False,
#             "text_input_required": False,
#         },
#     ),
#     name="slider_item",
# )
