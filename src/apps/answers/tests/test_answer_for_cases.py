import json
import uuid
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activity_flows.domain.flow_create import FlowCreate, FlowItemCreate
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.service.applet import AppletService
from apps.shared.enums import Language
from apps.shared.test.client import TestClient
from apps.themes.service import ThemeService
from apps.users.domain import User


@pytest.fixture
async def applet_data_with_flow(applet_minimal_data: AppletCreate) -> AppletCreate:
    data = applet_minimal_data.copy(deep=True)
    data.display_name = "schedule"
    # By some reasons for test need ActivityFlow
    data.activity_flows = [
        FlowCreate(
            name="flow",
            description={Language.ENGLISH: "description"},
            items=[FlowItemCreate(activity_key=data.activities[0].key)],
        )
    ]
    second_activity = data.activities[0].copy(deep=True)
    second_activity.name = data.activities[0].name + " second"
    data.activities.append(second_activity)
    return AppletCreate(**data.dict())


@pytest.fixture
async def applet_with_flow(
    session: AsyncSession, tom: User, applet_data_with_flow: AppletCreate
) -> AsyncGenerator[AppletFull, None]:
    srv = AppletService(session, tom.id)
    await ThemeService(session, tom.id).get_or_create_default()
    applet = await srv.create(applet_data_with_flow)
    yield applet


@pytest.mark.usefixtures("mock_kiq_report")
class TestAnswerCases:
    login_url = "/auth/login"
    answer_url = "/answers"

    async def test_answer_activity_items_create_for_respondent(
        self, client: TestClient, applet_with_flow: AppletFull, tom: User
    ):
        client.login(tom)

        submit_id = str(uuid.uuid4())
        answer_value_id = str(uuid.uuid4())

        create_data = dict(
            submit_id=submit_id,
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
            activity_id=applet_with_flow.activities[0].id,
            version=applet_with_flow.version,
            created_at=1681216969,
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=answer_value_id,
                        additional_text=None,
                    )
                ),
                events=json.dumps(dict(events=["event1", "event2"])),
                item_ids=[
                    applet_with_flow.activities[0].items[0].id,
                ],
                identifier="encrypted_identifier",
                scheduled_time=10,
                start_time=10,
                end_time=11,
            ),
            consent_to_share=False,
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()

        create_data = dict(
            submit_id=submit_id,
            applet_id=applet_with_flow.id,
            flow_id=applet_with_flow.activity_flows[0].id,
            activity_id=applet_with_flow.activities[1].id,
            version=applet_with_flow.version,
            created_at=1681216969,
            client=dict(
                appId="mindlogger-mobile",
                appVersion="0.21.48",
                width=819,
                height=1080,
            ),
            answer=dict(
                user_public_key="user key",
                answer=json.dumps(
                    dict(
                        value=answer_value_id,
                        additional_text=None,
                    )
                ),
                events=json.dumps(dict(events=["event1", "event2"])),
                item_ids=[
                    applet_with_flow.activities[1].items[0].id,
                ],
                identifier="encrypted_identifier",
                scheduled_time=10,
                start_time=10,
                end_time=11,
            ),
            consent_to_share=False,
        )

        response = await client.post(self.answer_url, data=create_data)
        assert response.status_code == 201, response.json()
