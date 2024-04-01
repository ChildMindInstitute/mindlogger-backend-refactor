import http
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.db.schemas import AlertSchema
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.db.schemas import AnswerSchema
from apps.applets.domain.applet_full import AppletFull
from apps.shared.test import BaseTest
from apps.subjects.domain import Subject
from apps.subjects.services import SubjectsService
from apps.users import User


@pytest.fixture()
async def lucy_alert_for_applet_three(session, lucy: User, applet_three: AppletFull) -> list[AlertSchema]:
    subject = await SubjectsService(session, lucy.id).get_by_user_and_applet(lucy.id, applet_three.id)
    assert subject
    answer = AnswerSchema(
        applet_id=applet_three.id,
        version=applet_three.version,
        submit_id=uuid.uuid4(),
        client={},
        applet_history_id=f"{applet_three.id}_{applet_three.version}",
        activity_history_id=f"{applet_three.activities[0].id}_{applet_three.version}",
        respondent_id=lucy.id,
        migrated_data={},
        target_subject_id=subject.id,
        source_subject_id=subject.id,
    )
    answer = await AnswersCRUD(session).create(answer)
    alerts = []
    for i in range(2):
        alert = AlertSchema(
            user_id=lucy.id,
            respondent_id=lucy.id,
            subject_id=subject.id,
            applet_id=applet_three.id,
            version=applet_three.version,
            activity_id=applet_three.activities[0].id,
            activity_item_id=applet_three.activities[0].items[0].id,
            answer_id=answer.id,
            alert_message="Test",
        )
        alerts.append(alert)
    await AlertCRUD(session).create_many(alerts)
    return alerts


@pytest.fixture()
async def lucy_subject(session: AsyncSession, lucy: User, applet_three: AppletFull) -> Subject:
    subject = await SubjectsService(session, lucy.id).get_by_user_and_applet(lucy.id, applet_three.id)
    assert subject
    return subject


class TestAlert(BaseTest):
    fixtures = [
        "alerts/fixtures/alerts.json",
        "workspaces/fixtures/workspaces.json",
    ]

    login_url = "/auth/login"
    alert_list_url = "/alerts"
    watch_alert_url = "/alerts/{alert_id}/is_watched"

    async def test_alert_get_all(
        self, session, client, lucy: User, lucy_alert_for_applet_three: list[AlertSchema], lucy_subject: Subject
    ):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")
        response = await client.get(self.alert_list_url)
        payload = response.json()
        assert response.status_code == http.HTTPStatus.OK
        assert payload["count"] == 2

    async def test_watch_alert(self, client):
        await client.login(self.login_url, "tom@mindlogger.com", "Test1234!")

        response = await client.post(self.watch_alert_url.format(alert_id="6f794861-0ff6-4c39-a3ed-602fd4e22c58"))
        assert response.status_code == http.HTTPStatus.OK

        response = await client.get(self.alert_list_url)
        assert response.status_code == http.HTTPStatus.OK
        assert response.json()["count"] == 2
        assert response.json()["result"][0]["isWatched"] is True

    async def test_alert_secret_id_from_subject(
        self, session, client, lucy: User, lucy_alert_for_applet_three: list[AlertSchema], lucy_subject: Subject
    ):
        await client.login(self.login_url, lucy.email_encrypted, "Test123")
        response = await client.get(self.alert_list_url)
        payload = response.json()
        assert response.status_code == http.HTTPStatus.OK
        assert payload["count"] == 2
        assert payload["result"][0]["secretId"] == lucy_subject.secret_user_id
