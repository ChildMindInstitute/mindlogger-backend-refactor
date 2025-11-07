import uuid
from typing import Self

from pydantic import model_validator

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
from apps.shared.domain import InternalModel, PublicModel


class ActivityItemUpdate(BaseActivityItem, PublicModel):
    id: uuid.UUID | None


class PreparedActivityItemUpdate(BaseActivityItem, InternalModel):
    id: uuid.UUID | None
    activity_id: uuid.UUID


class ActivityUpdate(ActivityBase, PublicModel):
    id: uuid.UUID | None
    key: uuid.UUID
    items: list[ActivityItemUpdate] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_existing_ids_for_duplicate(self) -> Self:
        items: list[ActivityItemUpdate] = self.items
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
    def validate_score_and_sections_conditional_logic(self) -> Self:
        validate_score_and_sections(self.items, self.scores_and_reports, self.subscale_setting)
        return self

    @model_validator(mode="after")
    def validate_subscales(self) -> Self:
        validate_subscales(self.items, self.subscale_setting)
        return self

    @model_validator(mode="before")
    @classmethod
    def validate_performance_task_type(cls, data: dict) -> dict:
        return validate_performance_task_type(data)

    @model_validator(mode="after")
    def validate_phrasal_templates(self) -> Self:
        validate_phrasal_templates(self.items)
        return self

    @model_validator(mode="after")
    def validate_request_health_record_data(self) -> Self:
        validate_request_health_record_data(self.items)
        return self


class ActivityReportConfiguration(PublicModel):
    report_included_item_name: str | None
