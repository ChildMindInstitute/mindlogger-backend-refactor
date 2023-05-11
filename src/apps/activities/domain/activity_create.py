import uuid

from pydantic import root_validator

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.activities.domain.conditions import (
    MultiSelectConditionType,
    SingleSelectConditionType,
)
from apps.activities.domain.response_type_config import ResponseType
from apps.activities.errors import (
    DuplicateActivityItemNameNameError,
    IncorrectConditionItemError,
    IncorrectConditionItemIndexError,
    IncorrectConditionLogicItemTypeError,
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
        item_names = [item.name for item in items]

        for index in range(len(items)):
            if items[index].conditional_logic is not None:
                for condition in items[index].conditional_logic.conditions:
                    # check if condition item name is in item names
                    if condition.item_name not in item_names:
                        raise IncorrectConditionItemError()
                    else:
                        # check if condition item order is less than current item order  # noqa: E501
                        condition_item_index = item_names.index(
                            condition.item_name
                        )
                        if condition_item_index > index:
                            raise IncorrectConditionItemIndexError()

                        # check if condition item type is correct
                        if items[condition_item_index].response_type not in [
                            ResponseType.SINGLESELECT,
                            ResponseType.MULTISELECT,
                            ResponseType.SLIDER,
                        ]:
                            raise IncorrectConditionLogicItemTypeError()

                        # check if condition option ids are correct
                        if condition.type in list(
                            SingleSelectConditionType
                        ) or list(MultiSelectConditionType):
                            option_ids = [
                                option.id
                                for option in items[
                                    condition_item_index
                                ].response_values.options
                            ]
                            if condition.payload.option_id not in option_ids:
                                raise IncorrectConditionOptionError()

        return values
