import datetime
import uuid

from apps.audit.crud import AuditLogCRUD
from apps.audit.db.schemas import AuditLogSchema
from broker import broker
from infrastructure.database import atomic, session_manager
from infrastructure.logger import logger


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
                await AuditLogCRUD(session).save(_build_schema(payload))
    except Exception as e:
        if retries > 0:
            logger.warning("audit_event_retry", retries_left=retries, error=str(e))
            await send_audit_event.kicker().with_labels(delay=5).kiq(payload, retries=retries - 1)
            return
        logger.error("audit_event_dropped", error=str(e), audit_event=payload)
        raise
