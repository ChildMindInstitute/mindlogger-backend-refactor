import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.audit.domain import AuditEvent
from apps.audit.enums import EventAction
from apps.audit.tasks import _resolve_actor_from_email
from apps.users.domain import User


def _payload(**overrides) -> dict:
    event = AuditEvent(
        event_action=EventAction.USER_SESSION_INVALID,
        user_id=None,
        user_email="tom@mindlogger.com",
    )
    payload = event.model_dump(mode="json")
    payload.update(overrides)
    return payload


async def test_resolves_failed_login_email_to_user(session: AsyncSession, tom: User):
    """A failed login carrying only an email is resolved to the account's user id."""
    resolved = await _resolve_actor_from_email(session, _payload())
    assert resolved == tom.id


async def test_unknown_email_is_not_resolved(session: AsyncSession, tom: User):
    """An unknown / typo'd email cannot be attributed and stays unresolved."""
    resolved = await _resolve_actor_from_email(session, _payload(**{"user.email": "nobody@nowhere.test"}))
    assert resolved is None


async def test_skips_when_actor_already_present(session: AsyncSession, tom: User):
    """Events with an authenticated actor are left untouched."""
    resolved = await _resolve_actor_from_email(session, _payload(**{"user.id": str(uuid.uuid4())}))
    assert resolved is None


async def test_skips_non_account_level_action(session: AsyncSession, tom: User):
    """Only account-level actions get email resolution."""
    payload = _payload(**{"event.action": EventAction.APPLET_ANSWER_VIEW.value})
    resolved = await _resolve_actor_from_email(session, payload)
    assert resolved is None
