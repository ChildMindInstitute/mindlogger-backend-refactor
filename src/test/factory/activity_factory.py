import uuid
from typing import List

from apps.activities.domain.activity_create import ActivityCreate, ActivityItemCreate
from apps.shared.enums import Language


def build_activity(items: List[ActivityItemCreate], **kwargs) -> ActivityCreate:
    attrs = {
        "key": uuid.uuid4(),
        "name": "Test Activity",
        "description": {Language.ENGLISH: "Test activity please ignore"},
    }
    attrs.update(kwargs)

    return ActivityCreate(**attrs, items=items)
