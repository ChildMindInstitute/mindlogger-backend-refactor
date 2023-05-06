import uuid

from pydantic import root_validator

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.activities.errors import (
    DuplicateActivityItemNameNameError,
    IncorrectConditionItemError,
    IncorrectConditionOptionError,
)
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
    def validate_conditional_logic(cls, values):
        items = values.get("items", [])
        item_names = set([item.name for item in items])

        for item in items:
            if item.conditional_logic:
                for condition in item.conditional_logic.conditions:
                    if condition.item_name not in item_names:
                        raise IncorrectConditionItemError()

        # TODO: validate condition option ids
