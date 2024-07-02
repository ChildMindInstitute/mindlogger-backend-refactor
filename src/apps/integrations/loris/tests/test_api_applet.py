import datetime
import uuid
from unittest.mock import AsyncMock, patch

from fastapi import BackgroundTasks

from apps.integrations.loris.api.applets import start_transmit_process
from apps.integrations.loris.domain import ActivitiesAndVisits, VisitsForUsers
from apps.shared.test.client import TestClient
from apps.users.domain import User


async def test_start_transmit_process(client: TestClient, user: User, uuid_zero: uuid.UUID, session):
    activity_with_visits = ActivitiesAndVisits(
        activity_id=uuid_zero,
        answer_id=uuid_zero,
        version="0.1.2",
        visit="test",
        activity_name="test",
        completed_date=datetime.datetime.now(),
    )
    vist_for_user = VisitsForUsers(user_id=uuid_zero, activities=[activity_with_visits], secret_user_id="test")
    with patch("apps.authentication.deps.get_current_user", return_value=user):
        with patch("infrastructure.database.deps.get_session", return_value=session):
            with patch("apps.integrations.loris.api.applets.integration", new_callable=AsyncMock) as mock_integration:
                background_tasks = BackgroundTasks()

                response = await start_transmit_process(
                    applet_id=uuid_zero,
                    users_and_visits=[vist_for_user],
                    background_tasks=background_tasks,
                    user=user,
                    session=session,
                )

                for task in background_tasks.tasks:
                    await task()

                assert response.status_code == 202
                mock_integration.assert_called_once_with(uuid_zero, session, user, [vist_for_user])
