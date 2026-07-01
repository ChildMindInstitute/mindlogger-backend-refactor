import datetime
import http
import uuid

import pytest
from pytest_mock import MockerFixture
from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.domain.applet_full import AppletFull
from apps.audit.crud import AuditLogCRUD
from apps.audit.domain import AuditEvent
from apps.audit.enums import EventAction
from apps.audit.tasks import _build_schema
from apps.shared.test.client import TestClient
from apps.users.domain import User

URL = "/audit/applets/{applet_id}/events"


@pytest.fixture(autouse=True)
def mock_audit_log(mocker: MockerFixture):
    """Stub the export endpoint's self-logging.

    The endpoint emits an ``applet:audit:export`` event via ``log()``. Under the
    in-memory test broker this runs the worker task synchronously, which would
    open its own DB session and write outside the test transaction. Mocking
    ``log`` keeps the test isolated and lets us assert the self-log separately.
    """
    return mocker.patch("apps.audit.api.log")


async def _seed_event(
    session: AsyncSession,
    applet_id: uuid.UUID,
    *,
    user_id: uuid.UUID,
    timestamp: datetime.datetime,
    event_id: uuid.UUID | None = None,
    action: EventAction = EventAction.APPLET_ANSWER_VIEW,
) -> AuditEvent:
    event = AuditEvent(
        event_action=action,
        user_id=user_id,
        curious_applet_id=[applet_id],
        timestamp=timestamp,
        event_id=event_id or uuid.uuid4(),
    )
    await AuditLogCRUD(session).save(_build_schema(event.model_dump(mode="json")))
    return event


async def _seed_account_event(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    timestamp: datetime.datetime,
    action: EventAction = EventAction.USER_SESSION_LOGIN,
    event_id: uuid.UUID | None = None,
) -> AuditEvent:
    """Seed an account-level event (no applet id), as already persisted with a
    resolved ``user_id``."""
    event = AuditEvent(
        event_action=action,
        user_id=user_id,
        timestamp=timestamp,
        event_id=event_id or uuid.uuid4(),
    )
    await AuditLogCRUD(session).save(_build_schema(event.model_dump(mode="json")))
    return event


async def test_unauthenticated_request_returns_401(client: TestClient, applet_one: AppletFull):
    response = await client.get(URL.format(applet_id=applet_one.id))
    assert response.status_code == http.HTTPStatus.UNAUTHORIZED


async def test_owner_can_export(client: TestClient, tom: User, applet_one: AppletFull):
    client.login(tom)
    response = await client.get(URL.format(applet_id=applet_one.id))
    assert response.status_code == http.HTTPStatus.OK, response.json()
    body = response.json()
    assert body["result"] == []
    assert body["count"] == 0


async def test_manager_can_export(client: TestClient, lucy: User, applet_one_lucy_manager: AppletFull):
    client.login(lucy)
    response = await client.get(URL.format(applet_id=applet_one_lucy_manager.id))
    assert response.status_code == http.HTTPStatus.OK, response.json()


async def test_coordinator_is_forbidden(client: TestClient, lucy: User, applet_one_lucy_coordinator: AppletFull):
    client.login(lucy)
    response = await client.get(URL.format(applet_id=applet_one_lucy_coordinator.id))
    assert response.status_code == http.HTTPStatus.FORBIDDEN


async def test_editor_is_forbidden(client: TestClient, lucy: User, applet_one_lucy_editor: AppletFull):
    client.login(lucy)
    response = await client.get(URL.format(applet_id=applet_one_lucy_editor.id))
    assert response.status_code == http.HTTPStatus.FORBIDDEN


async def test_invalid_date_range_returns_422(client: TestClient, tom: User, applet_one: AppletFull):
    client.login(tom)
    response = await client.get(
        URL.format(applet_id=applet_one.id),
        dict(fromDatetime="2026-05-10T14:30:00", toDatetime="2026-05-01T08:00:00"),
    )
    assert response.status_code == http.HTTPStatus.UNPROCESSABLE_ENTITY


async def test_returns_seeded_audit_event(client: TestClient, session: AsyncSession, tom: User, applet_one: AppletFull):
    event = await _seed_event(
        session,
        applet_one.id,
        user_id=tom.id,
        timestamp=datetime.datetime(2026, 5, 1, 10, 0, 0),
    )

    client.login(tom)
    response = await client.get(URL.format(applet_id=applet_one.id))
    assert response.status_code == http.HTTPStatus.OK
    body = response.json()
    assert body["count"] == 1
    assert body["result"][0]["event.id"] == str(event.event_id)
    assert body["result"][0]["event.action"] == EventAction.APPLET_ANSWER_VIEW.value
    assert body["result"][0]["user.id"] == str(tom.id)


async def test_returns_404_when_applet_missing(client: TestClient, tom: User):
    client.login(tom)
    response = await client.get(URL.format(applet_id=uuid.uuid4()))
    assert response.status_code == http.HTTPStatus.NOT_FOUND


async def test_date_range_filters_results(client: TestClient, session: AsyncSession, tom: User, applet_one: AppletFull):
    await _seed_event(session, applet_one.id, user_id=tom.id, timestamp=datetime.datetime(2026, 5, 1, 10, 0, 0))
    inside = await _seed_event(
        session, applet_one.id, user_id=tom.id, timestamp=datetime.datetime(2026, 5, 5, 10, 0, 0)
    )
    await _seed_event(session, applet_one.id, user_id=tom.id, timestamp=datetime.datetime(2026, 5, 10, 10, 0, 0))

    client.login(tom)
    response = await client.get(
        URL.format(applet_id=applet_one.id),
        dict(fromDatetime="2026-05-03T00:00:00", toDatetime="2026-05-07T00:00:00"),
    )
    assert response.status_code == http.HTTPStatus.OK
    body = response.json()
    assert body["count"] == 1
    assert body["result"][0]["event.id"] == str(inside.event_id)


async def test_owner_sees_own_account_event(
    client: TestClient, session: AsyncSession, tom: User, applet_one: AppletFull
):
    login = await _seed_account_event(session, user_id=tom.id, timestamp=datetime.datetime(2026, 5, 1, 10, 0, 0))

    client.login(tom)
    response = await client.get(URL.format(applet_id=applet_one.id))
    assert response.status_code == http.HTTPStatus.OK
    body = response.json()
    assert body["count"] == 1
    assert body["result"][0]["event.id"] == str(login.event_id)
    assert body["result"][0]["event.action"] == EventAction.USER_SESSION_LOGIN.value


async def test_owner_sees_manager_account_events(
    client: TestClient, session: AsyncSession, tom: User, lucy: User, applet_one_lucy_manager: AppletFull
):
    applet = applet_one_lucy_manager
    login = await _seed_account_event(session, user_id=lucy.id, timestamp=datetime.datetime(2026, 5, 1, 10, 0, 0))
    mfa = await _seed_account_event(
        session,
        user_id=lucy.id,
        timestamp=datetime.datetime(2026, 5, 1, 11, 0, 0),
        action=EventAction.USER_MFA_DISABLE,
    )
    # A failed login attributed (post-enrichment) to the manager.
    invalid = await _seed_account_event(
        session,
        user_id=lucy.id,
        timestamp=datetime.datetime(2026, 5, 1, 12, 0, 0),
        action=EventAction.USER_SESSION_INVALID,
    )

    client.login(tom)
    response = await client.get(URL.format(applet_id=applet.id))
    assert response.status_code == http.HTTPStatus.OK
    returned = {r["event.id"] for r in response.json()["result"]}
    assert returned == {str(login.event_id), str(mfa.event_id), str(invalid.event_id)}


async def test_owner_does_not_see_respondent_account_events(
    client: TestClient, session: AsyncSession, tom: User, lucy: User, applet_one_lucy_respondent: AppletFull
):
    applet = applet_one_lucy_respondent
    await _seed_account_event(session, user_id=lucy.id, timestamp=datetime.datetime(2026, 5, 1, 10, 0, 0))

    client.login(tom)
    response = await client.get(URL.format(applet_id=applet.id))
    assert response.status_code == http.HTTPStatus.OK
    assert response.json()["count"] == 0


async def test_owner_does_not_see_refresh_events(
    client: TestClient, session: AsyncSession, tom: User, applet_one: AppletFull
):
    await _seed_account_event(
        session,
        user_id=tom.id,
        timestamp=datetime.datetime(2026, 5, 1, 10, 0, 0),
        action=EventAction.USER_SESSION_REFRESH,
    )

    client.login(tom)
    response = await client.get(URL.format(applet_id=applet_one.id))
    assert response.status_code == http.HTTPStatus.OK
    assert response.json()["count"] == 0


async def test_export_self_logs_applet_audit_export(
    client: TestClient, tom: User, applet_one: AppletFull, mock_audit_log
):
    client.login(tom)
    response = await client.get(URL.format(applet_id=applet_one.id))
    assert response.status_code == http.HTTPStatus.OK

    mock_audit_log.assert_awaited_once()
    event = mock_audit_log.call_args[0][0]
    assert event.event_action == EventAction.APPLET_AUDIT_EXPORT
    assert event.user_id == tom.id
    assert event.curious_applet_id == [applet_one.id]
