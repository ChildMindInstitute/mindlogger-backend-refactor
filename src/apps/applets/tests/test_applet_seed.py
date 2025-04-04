import uuid
from unittest.mock import mock_open, patch

import pytest
import yaml
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.crud import ActivitiesCRUD
from apps.applets.commands.applet.applet import _seed
from apps.applets.crud import AppletsCRUD
from apps.schedule.crud.events import EventCRUD
from apps.schedule.crud.schedule_history import ScheduleHistoryCRUD
from apps.schedule.domain.constants import PeriodicityType
from apps.shared.test import BaseTest
from apps.subjects.crud import SubjectsCrud
from apps.users import UsersCRUD
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD


async def seed_config(config: str) -> None:
    m = mock_open(read_data=config)
    with patch("builtins.open", m):
        with open("test.yaml", "r") as f:
            data: dict = yaml.safe_load(f)
            await _seed(data, False)


class TestAppletSeedV1(BaseTest):
    async def test_seed_applet_successfully(self, session: AsyncSession):
        user_id = uuid.UUID("7e6c8635-3a16-48bd-ae0b-0ed89eb4be4d")
        user_email = "email@email.com"
        subject_id = uuid.UUID("3ac543d8-621e-46f4-bf60-fad188eeee72")
        applet_id = uuid.UUID("177dd712-fefb-4604-9f27-b69d88199d15")
        activity_id = uuid.UUID("db6b00e9-255d-49e5-92ac-c2ebe5241f81")
        event_id = uuid.UUID("0ba4d64a-afbb-4a94-b2fe-b8449a08e1f6")

        # language=yaml
        config = f"""
        version: "1.0"
        
        users:
          - id: {user_id}
            created_at: 2023-10-01T00:00:00Z
            email: {user_email}
            first_name: First
            last_name: Last
            password: password
        
        applets:
          - id: {applet_id}
            encryption:
                account_id: {user_id}
                base: ""
                prime: ""
                public_key: ""
            display_name: Back-Dated Applet 3
            description: This is a test applet created in the past
            created_at: 2023-10-01T00:00:00Z
            subjects:
              - id: {subject_id}
                created_at: 2023-10-01T00:00:00Z
                user_id: {user_id}
                email: {user_email}
                first_name: First
                last_name: Last
                secret_user_id: "123456"
                nickname: Applet Owner
                tag: "Team"
                roles: ["owner", "respondent"]
            activities:
              - id: {activity_id}
                name: Always Available Activity
                description: This is a test activity
                created_at: 2023-10-01T00:00:00Z
                auto_assign: true
                events:
                  - id: {event_id}
                    version: 20231001-1
                    created_at: 2023-10-01T00:00:00Z
                    periodicity: ALWAYS
                    start_time: 00:00:00
                    end_time: 23:59:00
                    one_time_completion: false
                  - id: {event_id}
                    version: 20231002-1
                    created_at: 2023-10-02T00:00:00Z
                    periodicity: DAILY
                    start_date: 2023-10-02
                    end_date: 2024-12-31
                    start_time: 00:00:00
                    end_time: 23:59:00
            report_server:
                ip_address: http://10.0.0.1
                public_key: Public key
                recipients: []
                include_user_id: false
                include_case_id: false
                email_body: Email body
        """
        await seed_config(config)

        # Check if the applet was created successfully
        await AppletsCRUD(session).get_by_id(applet_id)

        # Check if the user was created successfully
        await UsersCRUD(session).get_by_id(user_id)

        # Check if the user's workspace was created successfully
        workspace = await UserWorkspaceCRUD(session).get_by_user_id(user_id)
        assert workspace is not None

        # Check if the subject was created successfully
        subject = await SubjectsCrud(session).get_by_id(subject_id)
        assert subject is not None
        assert subject.user_id == user_id
        assert subject.applet_id == applet_id

        # Check if the activity was created successfully
        activity = await ActivitiesCRUD(session).get_by_id(activity_id)
        assert activity is not None

        # Check if the events were created successfully
        event = await EventCRUD(session).get_by_id(event_id)
        assert event.periodicity == PeriodicityType.DAILY
        assert event.version == "20231002-1"

        event_v1 = await ScheduleHistoryCRUD(session).get_by_id(f"{event_id}_20231001-1")
        assert event_v1 is not None

        event_v2 = await ScheduleHistoryCRUD(session).get_by_id(f"{event_id}_20231002-1")
        assert event_v2 is not None

    async def test_seed_invalid_version(self):
        # language=yaml
        config = """
        version: "2.0"
        """
        with pytest.raises(ValidationError) as info:
            await seed_config(config)

        assert info.value.args[0][0]._loc == "version"
