from sqlalchemy import REAL, Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database.base import Base

__all__ = ["ActivityItemSchema", "ActivityItemHistorySchema"]


class _BaseActivityItemSchema:
    name = Column(Text(), nullable=False)
    question = Column(JSONB())
    response_type = Column(Text())
    response_values = Column(JSONB())
    config = Column(JSONB(), default=dict())
    order = Column(REAL())

    """
    Text:
    header_image
    question
    response_type
    max_response_length
    correct_answer_required
    correct_answer
    skippable_item
    numerical_response_required
    response_data_identifier
    response_required
    remove_availability_to_go_back

    CheckBox:
    header_image
    question
    response_type
    token_value
    skippable_item
    set_alert
    option_score
    randomize_response_options
    remove_availability_to_go_back
    color_palette
    text_input_options
    text_input_options_required
    response_timer
    answers: [{value, token_value, score_value, tooltip, alert}]

    Slider:
    header_image
    question
    response_type
    min_value
    max_value
    min_label
    max_label
    tick_marks
    tick_mark_labels
    text_anchor
    skippable_item
    option_score
    set_alert
    use_continuous_slider

    Radio:
    header_image
    question
    response_type
    token_value
    skippable_item
    set_alert
    option_score
    remove_availability_to_go_back
    response_timer
    answers: [{value, token_value, score_value, tooltip, alert}]

    StackedRadio:
    header_image
    question
    response_type
    token_value
    skippable_item
    set_alert
    option_score
    remove_availability_to_go_back
    response_timer
    answers: {options: [], items: []}

    StackedCheckBox:
    header_image
    question
    response_type
    token_value
    skippable_item
    set_alert
    option_score
    randomize_response_options
    remove_availability_to_go_back
    color_palette
    text_input_options
    text_input_options_required
    response_timer
    answers: [{value, token_value, score_value, tooltip, alert}]
    """


class ActivityItemSchema(_BaseActivityItemSchema, Base):
    __tablename__ = "activity_items"

    activity_id = Column(
        ForeignKey("activities.id", ondelete="CASCADE"), nullable=False
    )


class ActivityItemHistorySchema(_BaseActivityItemSchema, Base):
    __tablename__ = "activity_item_histories"

    id = Column(UUID(as_uuid=True))
    id_version = Column(String(), primary_key=True)
    activity_id = Column(
        ForeignKey("activity_histories.id_version", ondelete="CASCADE"),
        nullable=False,
    )
