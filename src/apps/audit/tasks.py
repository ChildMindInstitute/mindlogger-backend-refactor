import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.audit.constants import ACCOUNT_LEVEL_EXPORT_ACTIONS
from apps.audit.crud import AuditLogCRUD
from apps.audit.db.schemas import AuditLogSchema
from apps.users.cruds.user import UsersCRUD
from broker import broker
from infrastructure.database import atomic, session_manager
from infrastructure.logger import logger


async def _resolve_actor_from_email(session: AsyncSession, payload: dict) -> uuid.UUID | None:
    """Resolve the denormalized ``user_id`` for an account-level event with no
    authenticated actor (e.g. a failed login carrying only ``user.email``), so the
    applet export can scope it. Only the column is populated; ``payload`` keeps
    ``user.id = null``. Unknown emails stay unresolved and are never exposed.
    """
    if payload.get("user.id") is not None:
        return None
    if payload.get("event.action") not in ACCOUNT_LEVEL_EXPORT_ACTIONS:
        return None
    email = payload.get("user.email")
    if not email:
        return None
    user = await UsersCRUD(session).get_user_or_none_by_email(email)
    return user.id if user else None


def _build_schema(payload: dict) -> AuditLogSchema:
    """Map the dotted-alias ECS payload to an ``AuditLogSchema`` row.

    The full payload is stored as-is in the JSONB ``payload`` column; a few
    fields are denormalized into typed columns for filtering and sorting.
    """
    timestamp = datetime.datetime.fromisoformat(payload["@timestamp"])
    if timestamp.tzinfo is not None:
        timestamp = timestamp.astimezone(datetime.timezone.utc).replace(tzinfo=None)

    user_id = payload.get("user.id")
    applet_ids = payload.get("curious.applet_id")

    return AuditLogSchema(
        event_id=uuid.UUID(payload["event.id"]),
        event_timestamp=timestamp,
        event_action=payload["event.action"],
        event_outcome=payload.get("event.outcome"),
        user_id=uuid.UUID(user_id) if user_id else None,
        applet_ids=[uuid.UUID(applet_id) for applet_id in applet_ids] if applet_ids else None,
        payload=payload,
    )


@broker.task()
async def send_audit_event(payload: dict, retries: int = 3) -> None:
    """Persist an audit event to Postgres.

    Retries on failure with a 5s delay; on final failure logs the payload
    so it is captured by the structured log pipeline (Datadog) instead of
    being silently dropped.
    """
    try:
        session_maker = session_manager.get_session()
        async with session_maker() as session:
            async with atomic(session):
                schema = _build_schema(payload)
                if schema.user_id is None:
                    schema.user_id = await _resolve_actor_from_email(session, payload)
                await AuditLogCRUD(session).save(schema)
    except Exception as e:
        if retries > 0:
            logger.warning("audit_event_retry", retries_left=retries, error=str(e))
            await send_audit_event.kicker().with_labels(delay=5).kiq(payload, retries=retries - 1)
            return
        logger.error("audit_event_dropped", error=str(e), audit_event=payload)
        raise
