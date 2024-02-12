import uuid

import pytest

from apps.activities.domain.activity_create import ActivityCreate, ActivityItemCreate
from apps.shared.enums import Language


@pytest.fixture
def activity_create(single_select_item_create: ActivityItemCreate) -> ActivityCreate:
    return ActivityCreate(
        name="test", description={Language.ENGLISH: "test"}, items=[single_select_item_create], key=uuid.uuid4()
    )


@pytest.fixture(scope="session")
def activity_create_session(item_create: ActivityItemCreate) -> ActivityCreate:
    return ActivityCreate(name="test", description={Language.ENGLISH: "test"}, items=[item_create], key=uuid.uuid4())
