from pydantic import Field

from apps.shared.domain import InternalModel

DEFAULT_ITEM_NAME = "test"


class BaseItemData(InternalModel):
    """We use this model just for annotations"""

    name: str = DEFAULT_ITEM_NAME
    question: dict[str, str] = Field(default_factory=dict)
    is_hidden: bool = False
