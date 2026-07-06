import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.applets.domain.applet_full import AppletFull
from apps.audit.crud import AuditLogCRUD
from apps.audit.domain import AuditEvent
from apps.audit.enums import EventAction
from apps.audit.query_service import AuditQueryService
from apps.audit.tasks import _build_schema
from apps.users.domain import User


def _make_event(
    applet_id: uuid.UUID,
    *,
    timestamp: datetime.datetime,
    event_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
) -> AuditEvent:
    return AuditEvent(
        event_action=EventAction.APPLET_ANSWER_VIEW,
        user_id=user_id or uuid.uuid4(),
        curious_applet_id=[applet_id],
        timestamp=timestamp,
        event_id=event_id or uuid.uuid4(),
    )


def _make_account_event(
    *,
    user_id: uuid.UUID,
    timestamp: datetime.datetime,
    action: EventAction = EventAction.USER_SESSION_LOGIN,
    event_id: uuid.UUID | None = None,
) -> AuditEvent:
    """An account-level event (login/MFA/...) that carries no applet id."""
    return AuditEvent(
        event_action=action,
        user_id=user_id,
        timestamp=timestamp,
        event_id=event_id or uuid.uuid4(),
    )


async def _seed(session: AsyncSession, event: AuditEvent) -> None:
    await AuditLogCRUD(session).save(_build_schema(event.model_dump(mode="json")))


async def test_filters_by_applet(session: AsyncSession):
    applet_id = uuid.uuid4()
    other_applet_id = uuid.uuid4()
    ts = datetime.datetime(2026, 5, 1, 10, 0, 0)

    await _seed(session, _make_event(applet_id, timestamp=ts))
    await _seed(session, _make_event(other_applet_id, timestamp=ts))

    events, total = await AuditQueryService(session).search_applet_events(applet_id)

    assert total == 1
    assert len(events) == 1
    assert events[0].curious_applet_id == [applet_id]


async def test_filters_by_date_range(session: AsyncSession):
    applet_id = uuid.uuid4()
    before = _make_event(applet_id, timestamp=datetime.datetime(2026, 5, 1, 10, 0, 0))
    inside = _make_event(applet_id, timestamp=datetime.datetime(2026, 5, 5, 10, 0, 0))
    after = _make_event(applet_id, timestamp=datetime.datetime(2026, 5, 10, 10, 0, 0))
    for event in (before, inside, after):
        await _seed(session, event)

    events, total = await AuditQueryService(session).search_applet_events(
        applet_id,
        from_datetime=datetime.datetime(2026, 5, 3, 0, 0, 0, tzinfo=datetime.timezone.utc),
        to_datetime=datetime.datetime(2026, 5, 7, 0, 0, 0, tzinfo=datetime.timezone.utc),
    )

    assert total == 1
    assert [e.event_id for e in events] == [inside.event_id]


async def test_results_sorted_by_timestamp_ascending(session: AsyncSession):
    applet_id = uuid.uuid4()
    third = _make_event(applet_id, timestamp=datetime.datetime(2026, 5, 9, 10, 0, 0))
    first = _make_event(applet_id, timestamp=datetime.datetime(2026, 5, 1, 10, 0, 0))
    second = _make_event(applet_id, timestamp=datetime.datetime(2026, 5, 5, 10, 0, 0))
    # Seed out of chronological order.
    for event in (third, first, second):
        await _seed(session, event)

    events, _ = await AuditQueryService(session).search_applet_events(applet_id)

    assert [e.event_id for e in events] == [first.event_id, second.event_id, third.event_id]


async def test_pagination(session: AsyncSession):
    applet_id = uuid.uuid4()
    seeded = []
    for day in range(1, 6):
        event = _make_event(applet_id, timestamp=datetime.datetime(2026, 5, day, 10, 0, 0))
        seeded.append(event)
        await _seed(session, event)

    page1, total = await AuditQueryService(session).search_applet_events(applet_id, page=1, limit=2)
    page2, _ = await AuditQueryService(session).search_applet_events(applet_id, page=2, limit=2)
    page3, _ = await AuditQueryService(session).search_applet_events(applet_id, page=3, limit=2)

    assert total == 5
    assert [e.event_id for e in page1] == [seeded[0].event_id, seeded[1].event_id]
    assert [e.event_id for e in page2] == [seeded[2].event_id, seeded[3].event_id]
    assert [e.event_id for e in page3] == [seeded[4].event_id]


async def test_returns_empty_when_no_events(session: AsyncSession):
    events, total = await AuditQueryService(session).search_applet_events(uuid.uuid4())
    assert events == []
    assert total == 0


async def test_includes_account_event_for_privileged_user(session: AsyncSession, tom: User, applet_one: AppletFull):
    """A login by a manager-class user of the applet is surfaced, even though it
    carries no applet id; the same event by a non-member is not."""
    ts = datetime.datetime(2026, 5, 1, 10, 0, 0)
    owner_login = _make_account_event(user_id=tom.id, timestamp=ts)
    stranger_login = _make_account_event(user_id=uuid.uuid4(), timestamp=ts)
    await _seed(session, owner_login)
    await _seed(session, stranger_login)

    events, total = await AuditQueryService(session).search_applet_events(applet_one.id)

    assert total == 1
    assert [e.event_id for e in events] == [owner_login.event_id]


async def test_excludes_refresh_account_event(session: AsyncSession, tom: User, applet_one: AppletFull):
    """USER_SESSION_REFRESH is deliberately kept out of the export."""
    ts = datetime.datetime(2026, 5, 1, 10, 0, 0)
    await _seed(session, _make_account_event(user_id=tom.id, timestamp=ts, action=EventAction.USER_SESSION_REFRESH))

    events, total = await AuditQueryService(session).search_applet_events(applet_one.id)

    assert total == 0
    assert events == []


async def test_mixes_applet_and_account_events(session: AsyncSession, tom: User, applet_one: AppletFull):
    """Applet-scoped and account-level events are returned together, in timestamp order."""
    account_event = _make_account_event(user_id=tom.id, timestamp=datetime.datetime(2026, 5, 1, 10, 0, 0))
    applet_event = _make_event(applet_one.id, user_id=tom.id, timestamp=datetime.datetime(2026, 5, 2, 10, 0, 0))
    await _seed(session, applet_event)
    await _seed(session, account_event)

    events, total = await AuditQueryService(session).search_applet_events(applet_one.id)

    assert total == 2
    assert [e.event_id for e in events] == [account_event.event_id, applet_event.event_id]


async def test_account_event_isolated_across_applets(
    session: AsyncSession,
    tom: User,
    lucy: User,
    applet_one_lucy_manager: AppletFull,
    applet_two: AppletFull,
):
    """An account event surfaces only in exports of applets the user is privileged
    on. lucy manages applet_one but has no role on applet_two, so her login must
    not leak into applet_two's export."""
    await _seed(session, _make_account_event(user_id=lucy.id, timestamp=datetime.datetime(2026, 5, 1, 10, 0, 0)))

    _, total_one = await AuditQueryService(session).search_applet_events(applet_one_lucy_manager.id)
    _, total_two = await AuditQueryService(session).search_applet_events(applet_two.id)

    assert total_one == 1
    assert total_two == 0


async def test_save_is_idempotent_on_event_id(session: AsyncSession):
    applet_id = uuid.uuid4()
    event = _make_event(applet_id, timestamp=datetime.datetime(2026, 5, 1, 10, 0, 0))

    await _seed(session, event)
    # Re-deliver the same event (simulating a worker retry).
    await _seed(session, event)

    events, total = await AuditQueryService(session).search_applet_events(applet_id)
    assert total == 1
    assert len(events) == 1
