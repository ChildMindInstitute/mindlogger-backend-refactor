import uuid
from typing import Self

from pydantic import Field, model_validator

from apps.activities.domain.activity_base import ActivityBase
from apps.activities.domain.activity_item_base import BaseActivityItem
from apps.activities.domain.custom_validation import (
    validate_item_flow,
    validate_performance_task_type,
    validate_phrasal_templates,
    validate_request_health_record_data,
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
    items: list[ActivityItemCreate] = Field(default_factory=list)
    extra_fields: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_existing_ids_for_duplicate(self) -> Self:
        items: list[ActivityItemCreate] = self.items
        item_names: set[str] = set()
        for item in items:
            if item.name in item_names:
                raise DuplicateActivityItemNameNameError()
            item_names.add(item.name)
        return self

    @model_validator(mode="after")
    def validate_item_flow_conditional_logic(self) -> Self:
        validate_item_flow(self.items)
        return self

    @model_validator(mode="after")
    def validate_scores_and_reports_conditional_logic(self) -> Self:
        validate_score_and_sections(self.items, self.scores_and_reports, self.subscale_setting)
        return self

    @model_validator(mode="after")
    def validate_subscales(self) -> Self:
        validate_subscales(self.items, self.subscale_setting)
        return self

    @model_validator(mode="after")
    def validate_performance_task_type(self) -> Self:
        # avoid recursive validation that would result from assigning self.performance_task_type = ...
        self.__dict__["performance_task_type"] = validate_performance_task_type(self.items, self.performance_task_type)
        return self

    @model_validator(mode="after")
    def validate_phrasal_templates(self) -> Self:
        validate_phrasal_templates(self.items)
        return self

    @model_validator(mode="after")
    def validate_request_health_record_data(self) -> Self:
        validate_request_health_record_data(self.items)
        return self
