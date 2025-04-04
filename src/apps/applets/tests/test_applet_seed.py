import uuid
from datetime import datetime
from typing import cast
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
from apps.authentication.services import AuthenticationService
from apps.schedule.crud.events import EventCRUD
from apps.schedule.crud.schedule_history import ScheduleHistoryCRUD
from apps.schedule.domain.constants import PeriodicityType
from apps.shared.test import BaseTest
from apps.subjects.crud import SubjectsCrud
from apps.subjects.domain import Subject
from apps.users import User, UsersCRUD
from apps.users.domain import UserCreate
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD


async def seed_config(config: str) -> None:
    m = mock_open(read_data=config)
    with patch("builtins.open", m):
        with open("test.yaml", "r") as f:
            data: dict = yaml.safe_load(f)
    await _seed(data, False)


def uuid_prefix() -> str:
    return str(uuid.uuid4()).replace("-", "")[:8]


def user_details(last_name: str) -> dict:
    return {
        "id": uuid.uuid4(),
        "email": f"{last_name.lower()}{uuid_prefix()}@email.com",
        "first_name": "Example",
        "last_name": last_name,
        "password": "password",
        "subject_id": uuid.uuid4(),
        "secret_user_id": uuid.uuid4(),
        "nickname": f"Applet {last_name}",
    }


class TestAppletSeedV1(BaseTest):
    async def test_seed_applet_successfully(self, session: AsyncSession):
        base = "[2]"
        prime = (
            "[246,25,62,57,3,211,201,60,45,201,150,1,190,238,76,102,74,251,46,148,77,29,170,58,244,105,8,98,210,"
            "151,133,169,246,23,82,120,229,35,147,74,213,4,72,145,136,233,32,137,37,224,243,5,139,4,160,166,149,"
            "244,212,219,224,247,214,181,167,166,108,86,34,111,18,209,99,87,0,176,210,79,16,216,191,44,55,132,214,"
            "25,245,124,98,228,240,133,112,89,169,47,151,247,250,57,221,161,14,109,147,162,179,95,51,145,147,18,"
            "195,48,190,74,88,26,132,25,66,236,103,148,101,136,234,195]"
        )
        public_key = (
            "[239,242,164,45,219,53,182,152,239,29,82,154,249,100,131,121,96,86,0,20,36,150,45,34,36,235,201,"
            "3,250,82,44,145,87,153,223,175,96,63,93,62,107,143,34,120,13,237,165,86,39,170,168,169,141,120,"
            "229,181,72,41,73,18,150,141,154,32,17,174,63,44,159,161,63,9,249,247,90,125,232,219,130,6,250,"
            "243,69,11,253,29,234,155,198,255,62,115,100,61,129,28,24,2,22,155,104,117,210,159,229,94,112,"
            "238,97,145,47,98,2,194,193,121,209,190,229,89,44,227,167,9,131,245,151,87]"
        )
        applet_id = uuid.uuid4()
        applet_display_name = f"Back-Dated Applet {uuid_prefix()}"

        owner = {
            "id": uuid.UUID("2b14f59e-baf6-407b-9b59-25ec39bc3893"),
            "email": "someone@example.com",
            "first_name": "Someone",
            "last_name": "Owner",
            "password": "password",
            "subject_id": uuid.uuid4(),
            "secret_user_id": uuid.uuid4(),
            "nickname": "Applet Owner",
        }
        manager = user_details("Manager")
        coordinator = user_details("Coordinator")
        editor = user_details("Editor")
        reviewer = user_details("Reviewer")
        full_account_respondent = user_details("Respondent")
        limited_account_subject_id = uuid.uuid4()

        users = {
            "owner": owner,
            "manager": manager,
            "coordinator": coordinator,
            "editor": editor,
            "reviewer": reviewer,
            "respondent": full_account_respondent,
        }
        users_snippet = ""
        subjects_snippet = ""
        for role, user in users.items():
            users_snippet += f"""
  - id: &{role}_id {user.get("id")}
    created_at: 2023-10-01T00:00:00Z
    email: &{role}_email {user.get("email")}
    first_name: {user.get("first_name")}
    last_name: {user.get("last_name")}
    password: {user.get("password")}"""

            subjects_snippet += f"""
      - id: {user.get("subject_id")}
        created_at: 2023-10-01T00:00:00Z
        user_id: *{role}_id
        email: *{role}_email
        first_name: {user.get("first_name")}
        last_name: {user.get("last_name")}
        secret_user_id: {user.get("secret_user_id")}
        nickname: {user.get("nickname")}"""

            if role != "respondent":
                subjects_snippet += f"""
        tag: "Team"
        roles: ["{role}", "respondent"]"""
            else:
                subjects_snippet += """
        roles: ["respondent"]"""

        subjects_snippet += f"""
      - id: {limited_account_subject_id}
        created_at: 2023-10-01T00:00:00Z
        first_name: Limited
        last_name: Account
        secret_user_id: {uuid.uuid4()}
        nickname: Limited Account
"""

        activities = {
            "always": {
                "id": uuid.uuid4(),
                "name": "Always Available Activity",
                "description": "This is a test activity",
                "created_at": "2023-10-01T00:00:00Z",
                "events": [
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-01T00:00:00Z",
                        "version": "20231001-1",
                        "periodicity": PeriodicityType.ALWAYS,
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-02T00:00:00Z",
                        "version": "20231002-1",
                        "periodicity": PeriodicityType.DAILY,
                        "start_date": "2023-10-02",
                        "end_date": "2026-12-31",
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2025-01-01T00:00:00Z",
                        "version": "20250101-1",
                        "periodicity": PeriodicityType.ALWAYS,
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                ],
            },
            "once": {
                "id": uuid.uuid4(),
                "name": "Once Activity",
                "description": "This is a test activity",
                "created_at": "2023-10-01T00:00:00Z",
                "events": [
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-01T00:00:00Z",
                        "version": "20231001-1",
                        "periodicity": PeriodicityType.ALWAYS,
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-01T00:00:00Z",
                        "version": "20231001-2",
                        "periodicity": PeriodicityType.ONCE,
                        "selected_date": "2023-10-01",
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                ],
            },
            "daily": {
                "id": uuid.uuid4(),
                "name": "Daily Activity",
                "description": "This is a test activity",
                "created_at": "2023-10-01T00:00:00Z",
                "events": [
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-01T00:00:00Z",
                        "version": "20231001-1",
                        "periodicity": PeriodicityType.ALWAYS,
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-01T00:00:00Z",
                        "version": "20231001-2",
                        "periodicity": PeriodicityType.DAILY,
                        "start_date": "2023-10-01",
                        "end_date": "2026-12-31",
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                ],
            },
            "weekly": {
                "id": uuid.uuid4(),
                "name": "Weekly Activity",
                "description": "This is a test activity",
                "created_at": "2023-10-01T00:00:00Z",
                "events": [
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-01T00:00:00Z",
                        "version": "20231001-1",
                        "periodicity": PeriodicityType.ALWAYS,
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-01T00:00:00Z",
                        "version": "20231001-2",
                        "periodicity": PeriodicityType.WEEKLY,
                        "start_date": "2023-10-01",
                        "end_date": "2026-12-31",
                        "selected_date": "2023-10-01",
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                ],
            },
            "weekdays": {
                "id": uuid.uuid4(),
                "name": "Weekdays Activity",
                "description": "This is a test activity",
                "created_at": "2023-10-01T00:00:00Z",
                "events": [
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-01T00:00:00Z",
                        "version": "20231001-1",
                        "periodicity": PeriodicityType.ALWAYS,
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-01T00:00:00Z",
                        "version": "20231001-2",
                        "periodicity": PeriodicityType.WEEKDAYS,
                        "start_date": "2023-10-01",
                        "end_date": "2026-12-31",
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                ],
            },
            "monthly": {
                "id": uuid.uuid4(),
                "name": "Monthly Activity",
                "description": "This is a test activity",
                "created_at": "2023-10-01T00:00:00Z",
                "events": [
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-01T00:00:00Z",
                        "version": "20231001-1",
                        "periodicity": PeriodicityType.ALWAYS,
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                    {
                        "id": uuid.uuid4(),
                        "created_at": "2023-10-01T00:00:00Z",
                        "version": "20231001-2",
                        "periodicity": PeriodicityType.MONTHLY,
                        "start_date": "2023-10-01",
                        "end_date": "2026-12-31",
                        "selected_date": "2023-10-01",
                        "start_time": "00:00:00",
                        "end_time": "23:59:00",
                    },
                ],
            },
        }
        activities_snippet = ""
        for activity in activities.values():
            activities_snippet += f"""
      - id: {activity["id"]}
        name: {activity["name"]}
        description: {activity["description"]}
        created_at: {activity["created_at"]}"""

            events_snippet = """
        events:"""
            for event in activity["events"]:  # type: ignore[attr-defined]
                events_snippet += f"""
          - id: {event["id"]}
            version: {event["version"]}
            created_at: {event["created_at"]}
            periodicity: {event["periodicity"]}
            start_time: {event["start_time"]}
            end_time: {event["end_time"]}"""

                if event.get("start_date"):
                    events_snippet += f"""
            start_date: {event["start_date"]}"""
                if event.get("end_date"):
                    events_snippet += f"""
            end_date: {event["end_date"]}"""
                if event.get("selected_date"):
                    events_snippet += f"""
            selected_date: {event["selected_date"]}"""

            activities_snippet += events_snippet

        # language=yaml
        config = f"""version: "1.0"

users: {users_snippet}

applets:
  - id: {applet_id}
    encryption:
      account_id: *owner_id
      base: "{base}"
      prime: "{prime}"
      public_key: "{public_key}"
    display_name: {applet_display_name}
    description: This is a test applet created in the past
    created_at: 2023-10-01T00:00:00Z
    subjects: {subjects_snippet}
    activities: {activities_snippet}
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

        workspace_crud = UserWorkspaceCRUD(session)
        auth_service = AuthenticationService(session)
        subjects_crud = SubjectsCrud(session)

        # Check if the users and their subjects were created successfully
        for user in users.values():
            # Check if the user was created successfully
            created_user = await UsersCRUD(session).get_by_id(user["id"])
            assert created_user is not None
            assert created_user.id == user["id"]
            assert created_user.email_encrypted == user["email"]
            assert created_user.first_name == user["first_name"]
            assert created_user.last_name == user["last_name"]
            assert (
                auth_service.verify_password(user["password"], created_user.hashed_password, raise_exception=False)
                is True
            )

            # Check if the user's workspace was created successfully
            workspace = await workspace_crud.get_by_user_id(created_user.id)
            assert workspace is not None

            subject = await subjects_crud.get_by_id(user["subject_id"])
            assert subject is not None
            assert subject.user_id == user["id"]
            assert subject.applet_id == applet_id

        limited_account_subject = await subjects_crud.get_by_id(limited_account_subject_id)
        assert limited_account_subject is not None
        assert limited_account_subject.user_id is None
        assert limited_account_subject.email is None
        assert limited_account_subject.applet_id == applet_id

        # Confirm access roles
        access_crud = UserAppletAccessCRUD(session)
        owner_roles = await access_crud.get_user_roles_to_applet(cast(uuid.UUID, owner["id"]), applet_id)
        assert set(owner_roles) == {"owner", "respondent"}

        manager_roles = await access_crud.get_user_roles_to_applet(manager["id"], applet_id)
        assert set(manager_roles) == {"manager", "respondent"}

        coordinator_roles = await access_crud.get_user_roles_to_applet(coordinator["id"], applet_id)
        assert set(coordinator_roles) == {"coordinator", "respondent"}

        editor_roles = await access_crud.get_user_roles_to_applet(editor["id"], applet_id)
        assert set(editor_roles) == {"editor", "respondent"}

        reviewer_roles = await access_crud.get_user_roles_to_applet(reviewer["id"], applet_id)
        assert set(reviewer_roles) == {"reviewer", "respondent"}

        respondent_roles = await access_crud.get_user_roles_to_applet(full_account_respondent["id"], applet_id)
        assert set(respondent_roles) == {"respondent"}

        # Check if the activities were created successfully
        for activity in activities.values():
            schema_activity = await ActivitiesCRUD(session).get_by_id(cast(uuid.UUID, activity["id"]))
            assert schema_activity is not None
            assert schema_activity.name == activity["name"]

            current_event = activity["events"][-1]  # type: ignore[index]
            schema_event = await EventCRUD(session).get_by_id(current_event["id"])
            time_format = "%H:%M:%S"
            start_time = datetime.strptime(current_event["start_time"], time_format).time()
            end_time = datetime.strptime(current_event["end_time"], time_format).time()
            assert schema_event is not None
            assert schema_event.periodicity == current_event["periodicity"]
            assert schema_event.version == current_event["version"]
            assert schema_event.start_time == start_time
            assert schema_event.end_time == end_time

            for event in activity["events"]:  # type: ignore[attr-defined]
                history_schema = await ScheduleHistoryCRUD(session).get_by_id(f"{event['id']}_{event['version']}")
                assert history_schema is not None

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


# Things to validate
## AppletConfigFileV1
### - Duplicate users IDs ✅
### - Duplicate users emails ✅
### - Duplicate applet IDs ✅
### - Applets with IDs that are already in the database ✅
### - Applets with names that are already in the database ✅
### - Applets with no activities ✅
### - Subjects with user IDs that are not defined in the users section ✅
### - Subjects with IDs that are already in the database ✅
### - Subjects with secret IDs that are not unique ✅
### - Applets with no owner ✅
### - Applets with multiple owners ✅
### - Duplicate subject IDs ✅
### - Activities where the first event does not have a periodicity of ALWAYS ✅
### - Activities where the first event is not on the default schedule ✅
### - Each subject must have a respondent role ✅
### - Roles array must not be empty
### - Subject role must be one of the valid options
### - Subject tag must be valid
### - Full account subjects must have at least respondent role
### - Limited subjects should not have any roles
### - User exists in the database and is deleted
### - User exists in the database with the same email but has different id
### - User exists in the database with the same ID but has different email
### - User exists in the database with the same ID but has different first_name
### - User exists in the database with the same ID but has different last_name
### - User exists in the database with the same ID but has different password
### - Event with version specified alone
### - Event with created_at specified alone
