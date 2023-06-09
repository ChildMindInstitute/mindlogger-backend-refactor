import uuid

from pydantic import root_validator

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.activities.domain.custom_validation import (
    validate_item_flow,
    validate_score_and_sections,
    validate_subscales,
)
from apps.activities.errors import DuplicateActivityItemNameNameError
from apps.shared.domain import InternalModel


class ActivityItemCreate(BaseActivityItem, InternalModel):
    pass


class PreparedActivityItemCreate(BaseActivityItem, InternalModel):
    activity_id: uuid.UUID


class ActivityCreate(ActivityBase, InternalModel):
    key: uuid.UUID
    items: list[ActivityItemCreate]

    @root_validator()
    def validate_existing_ids_for_duplicate(cls, values):
        items = values.get("items", [])

        item_names = set()
        for item in items:  # type:ActivityItemCreate
            if item.name in item_names:
                raise DuplicateActivityItemNameNameError()
            item_names.add(item.name)
        return values

    @root_validator()
    def validate_item_flow_conditional_logic(cls, values):
        return validate_item_flow(values)

    @root_validator()
    def validate_score_and_sections_conditional_logic(cls, values):
        return validate_score_and_sections(values)

    @root_validator()
    def validate_subscales(cls, values):
        return validate_subscales(values)
