import uuid
from typing import Any

from pydantic import Field, root_validator

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.activities.domain.custom_validation import (
    validate_item_flow,
    validate_performance_task_type,
    validate_phrasal_templates,
    validate_score_and_sections,
    validate_subscales,
)
from apps.activities.errors import DuplicateActivityItemNameNameError
from apps.shared.domain import InternalModel


class ActivityItemCreate(BaseActivityItem, InternalModel):
    extra_fields: dict = Field(default_factory=dict)


class PreparedActivityItemCreate(BaseActivityItem, InternalModel):
    activity_id: uuid.UUID
    extra_fields: dict = Field(default_factory=dict)


class ActivityCreate(ActivityBase, InternalModel):
    key: uuid.UUID
    items: list[ActivityItemCreate]
    extra_fields: dict = Field(default_factory=dict)

    @root_validator()
    def validate_existing_ids_for_duplicate(cls, values) -> list[Any]:
        items: list[ActivityItemCreate] = values.get("items", [])

        item_names = set()
        for item in items:
            if item.name in item_names:
                raise DuplicateActivityItemNameNameError()
            item_names.add(item.name)
        return values

    @root_validator()
    def validate_item_flow_conditional_logic(cls, values):
        return validate_item_flow(values)

    @root_validator()
    def validate_scores_and_reports_conditional_logic(cls, values):
        return validate_score_and_sections(values)

    @root_validator()
    def validate_subscales(cls, values):
        return validate_subscales(values)

    @root_validator()
    def validate_performance_task_type(cls, values):
        return validate_performance_task_type(values)

    @root_validator()
    def validate_phrasal_templates(cls, values):
        return validate_phrasal_templates(values)
