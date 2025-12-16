from typing import Annotated

from pydantic import Field

from apps.shared.domain import InternalModel, PublicModel

__all__ = [
    "ActivityFlowItemHistoryChange",
    "ActivityFlowHistoryChange",
    "PublicActivityFlowHistoryChange",
]


class ActivityFlowItemHistoryChange(InternalModel):
    name: str | None = None
    changes: list[str] | None = None


class ActivityFlowHistoryChange(InternalModel):
    name: str | None = None
    changes: Annotated[list[str] | None, Field(default_factory=list)]
    items: Annotated[list[ActivityFlowItemHistoryChange] | None, Field(default_factory=list)]


class PublicActivityFlowHistoryChange(PublicModel):
    name: str | None = None
    changes: Annotated[list[str] | None, Field(default_factory=list)]
    items: Annotated[list[ActivityFlowItemHistoryChange] | None, Field(default_factory=list)]
