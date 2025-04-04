import uuid
from unittest.mock import mock_open, patch

import pytest
import yaml
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.crud import ActivitiesCRUD
from apps.applets.commands.applet.applet import _seed
from apps.applets.commands.applet.seed.errors import (
    AppletAlreadyExistsError,
    AppletNameAlreadyExistsError,
    DuplicatAppletIdsError,
    DuplicateUserEmailsError,
    DuplicateUserIdsError,
    FullAccountWithoutRespondentRoleError,
    InvalidAppletError,
    InvalidFirstEventError,
    SubjectIdAlreadyExistsError,
    SubjectUserNotPresentError,
)
from apps.applets.crud import AppletsCRUD
from apps.applets.domain.applet_full import AppletFull
from apps.schedule.crud.events import EventCRUD
from apps.schedule.crud.schedule_history import ScheduleHistoryCRUD
from apps.schedule.domain.constants import PeriodicityType
from apps.shared.test import BaseTest
from apps.subjects.crud import SubjectsCrud
from apps.subjects.domain import Subject
from apps.users import User, UsersCRUD
from apps.users.domain import UserCreate
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD


async def seed_config(config: str) -> None:
    m = mock_open(read_data=config)
    with patch("builtins.open", m):
        with open("test.yaml", "r") as f:
            data: dict = yaml.safe_load(f)
            await _seed(data, False)


def uuid_prefix() -> str:
    return str(uuid.uuid4()).replace("-", "")[:8]


class TestAppletSeedV1(BaseTest):
    async def test_seed_applet_successfully(self, session: AsyncSession):
        user_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"
        subject_id = uuid.uuid4()
        applet_id = uuid.uuid4()
        applet_name = f"Back-Dated Applet {uuid_prefix()}"
        activity_id = uuid.uuid4()
        event_id = uuid.uuid4()

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
            display_name: {applet_name}
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

        errors = info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("version",)
        assert errors[0]["msg"] == "unexpected value; permitted: '1.0'"

    async def test_seed_duplicate_user_ids(self):
        user_id = uuid.UUID("7e6c8635-3a16-48bd-ae0b-0ed89eb4be4d")

        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {user_id}
              created_at: 2023-10-01T00:00:00Z
              email: user1@example.com
              first_name: First
              last_name: Last
              password: password
            - id: {user_id}
              created_at: 2023-10-01T00:00:00Z
              email: user2@example.com
              first_name: First
              last_name: Last
              password: password
        """
        with pytest.raises(DuplicateUserIdsError):
            await seed_config(config)

    async def test_seed_duplicate_user_emails(self):
        user_email = "email@example.com"

        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {uuid.uuid4()}
              created_at: 2023-10-01T00:00:00Z
              email: {user_email}
              first_name: First
              last_name: Last
              password: password
            - id: {uuid.uuid4()}
              created_at: 2023-10-01T00:00:00Z
              email: {user_email}
              first_name: First
              last_name: Last
              password: password
        """
        with pytest.raises(DuplicateUserEmailsError):
            await seed_config(config)

    async def test_seed_duplicate_applet_ids(self):
        user_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"
        applet_id = uuid.uuid4()

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
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {uuid.uuid4()}
                  user_id: {user_id}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["owner", "respondent"]
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
            - id: {applet_id}
              encryption:
                  account_id: {user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {uuid.uuid4()}
                  user_id: {user_id}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "1234567"
                  roles: ["owner", "respondent"]
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(DuplicatAppletIdsError):
            await seed_config(config)

    async def test_seed_existing_applet_id(self, applet_one: AppletFull):
        user_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"

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
            - id: {applet_one.id}
              encryption:
                  account_id: {user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {uuid.uuid4()}
                  user_id: {user_id}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["owner", "respondent"]
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(AppletAlreadyExistsError):
            await seed_config(config)

    async def test_seed_existing_applet_name(self, applet_one: AppletFull, tom: User, tom_create: UserCreate):
        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {tom.id}
              email: {tom_create.email}
              first_name: {tom.first_name}
              last_name: {tom.last_name}
              password: {tom_create.password}

        applets:
            - id: {uuid.uuid4()}
              encryption:
                  account_id: {tom.id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: {applet_one.display_name}
              subjects:
                - id: {uuid.uuid4()}
                  user_id: {tom.id}
                  email: {tom_create.email}
                  first_name: {tom.first_name}
                  last_name: {tom.last_name}
                  secret_user_id: "123456"
                  roles: ["owner", "respondent"]
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(AppletNameAlreadyExistsError):
            await seed_config(config)

    async def test_seed_applet_no_activities(self):
        user_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"

        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {user_id}
              email: {user_email}
              first_name: First
              last_name: Last
              password: password

        applets:
            - id: {uuid.uuid4()}
              encryption:
                  account_id: {user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {uuid.uuid4()}
                  user_id: {user_id}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["owner", "respondent"]
              activities: []
        """
        with pytest.raises(ValidationError) as info:
            await seed_config(config)

        errors = info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("applets", 0, "activities")
        assert errors[0]["msg"] == "ensure this value has at least 1 items"

    async def test_seed_undefined_subject_user(self):
        user_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"

        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {user_id}
              email: {user_email}
              first_name: First
              last_name: Last
              password: password

        applets:
            - id: {uuid.uuid4()}
              encryption:
                  account_id: {user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {uuid.uuid4()}
                  user_id: {uuid.uuid4()}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["owner", "respondent"]
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(SubjectUserNotPresentError):
            await seed_config(config)

    async def test_seed_already_existing_subject(self, tom_create: UserCreate, tom_applet_one_subject: Subject):
        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {tom_applet_one_subject.user_id}
              email: {tom_create.email}
              first_name: {tom_create.first_name}
              last_name: {tom_create.last_name}
              password: {tom_create.password}

        applets:
            - id: {uuid.uuid4()}
              encryption:
                  account_id: {tom_applet_one_subject.user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {tom_applet_one_subject.id}
                  user_id: {tom_applet_one_subject.user_id}
                  email: {tom_create.email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["owner", "respondent"]
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(SubjectIdAlreadyExistsError):
            await seed_config(config)

    async def test_seed_duplicate_subject_secret_ids(self):
        user_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"

        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {user_id}
              email: {user_email}
              first_name: First
              last_name: Last
              password: password

        applets:
            - id: {uuid.uuid4()}
              encryption:
                  account_id: {user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {uuid.uuid4()}
                  user_id: {user_id}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["owner", "respondent"]
                - id: {uuid.uuid4()}
                  first_name: Limited
                  last_name: Account
                  secret_user_id: "123456"
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(InvalidAppletError) as info:
            await seed_config(config)

        assert "The secret user IDs are repeated" in info.value.args[0]

    async def test_seed_applet_without_owner(self):
        user_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"

        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {user_id}
              email: {user_email}
              first_name: First
              last_name: Last
              password: password

        applets:
            - id: {uuid.uuid4()}
              encryption:
                  account_id: {user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {uuid.uuid4()}
                  user_id: {user_id}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["respondent"]
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(InvalidAppletError) as info:
            await seed_config(config)

        assert "Must have exactly one owner, found 0 owners" in info.value.args[0]

    async def test_seed_applet_with_multiple_owners(self):
        user_id = uuid.uuid4()
        user2_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"
        user2_email = f"email_{uuid_prefix()}@email.com"

        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {user_id}
              email: {user_email}
              first_name: First
              last_name: Last
              password: password
            - id: {user2_id}
              email: {user2_email}
              first_name: First
              last_name: Last
              password: password

        applets:
            - id: {uuid.uuid4()}
              encryption:
                  account_id: {user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {uuid.uuid4()}
                  user_id: {user_id}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["owner", "respondent"]
                - id: {uuid.uuid4()}
                  user_id: {user2_id}
                  email: {user2_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "1234567"
                  roles: ["owner", "respondent"]
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(InvalidAppletError) as info:
            await seed_config(config)

        assert "Must have exactly one owner, found 2 owners" in info.value.args[0]

    async def test_seed_duplicate_subject_ids(self):
        user_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"
        subject_id = uuid.uuid4()

        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {user_id}
              email: {user_email}
              first_name: First
              last_name: Last
              password: password

        applets:
            - id: {uuid.uuid4()}
              encryption:
                  account_id: {user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {subject_id}
                  user_id: {user_id}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["owner", "respondent"]
                - id: {subject_id}
                  first_name: Limited
                  last_name: Account
                  secret_user_id: "1234567"
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(InvalidAppletError) as info:
            await seed_config(config)

        assert "The subject IDs are repeated" in info.value.args[0]

    async def test_seed_invalid_first_event_periodicity(self):
        user_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"

        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {user_id}
              email: {user_email}
              first_name: First
              last_name: Last
              password: password

        applets:
            - id: {uuid.uuid4()}
              encryption:
                  account_id: {user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {uuid.uuid4()}
                  user_id: {user_id}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["owner", "respondent"]
              activities:
                - id: {uuid.uuid4()}
                  name: Daily Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: DAILY
                      start_date: 2023-10-01
                      end_date: 2024-12-31
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(InvalidFirstEventError) as info:
            await seed_config(config)

        assert "Periodicity must be set to ALWAYS" in info.value.args[0]

    async def test_seed_invalid_first_event_schedule(self):
        user_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"

        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {user_id}
              email: {user_email}
              first_name: First
              last_name: Last
              password: password

        applets:
            - id: {uuid.uuid4()}
              encryption:
                  account_id: {user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {uuid.uuid4()}
                  user_id: {user_id}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["owner", "respondent"]
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      user_id: {user_id}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(InvalidFirstEventError) as info:
            await seed_config(config)

        assert "Must be on the default schedule" in info.value.args[0]

    async def test_seed_subject_missing_respondent_role(self):
        user_id = uuid.uuid4()
        user_email = f"email_{uuid_prefix()}@email.com"
        subject_id = uuid.uuid4()

        # language=yaml
        config = f"""
        version: "1.0"
        users:
            - id: {user_id}
              email: {user_email}
              first_name: First
              last_name: Last
              password: password

        applets:
            - id: {uuid.uuid4()}
              encryption:
                  account_id: {user_id}
                  base: ""
                  prime: ""
                  public_key: ""
              display_name: Back-Dated Applet {uuid_prefix()}
              subjects:
                - id: {subject_id}
                  user_id: {user_id}
                  email: {user_email}
                  first_name: First
                  last_name: Last
                  secret_user_id: "123456"
                  roles: ["owner"]
              activities:
                - id: {uuid.uuid4()}
                  name: Always Available Activity
                  events:
                    - id: {uuid.uuid4()}
                      version: 20231001-1
                      created_at: 2023-10-01T00:00:00Z
                      periodicity: ALWAYS
                      start_time: 00:00:00
                      end_time: 23:59:00
        """
        with pytest.raises(FullAccountWithoutRespondentRoleError):
            await seed_config(config)

