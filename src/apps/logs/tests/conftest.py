from typing import Any

import pytest

from apps.logs.domain.constants import UserActivityEvent, UserActivityEventType
from infrastructure.http.domain import MindloggerContentSource


@pytest.fixture
def base_log_data() -> dict[str, Any]:
    return {
        "firebase_token_id": None,
        "event": UserActivityEvent.LOGIN,
        "event_type": UserActivityEventType.LOGIN,
        "user_agent": "test",
        "mindlogger_content": MindloggerContentSource.undefined,
    }
