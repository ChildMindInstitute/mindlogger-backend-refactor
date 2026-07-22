from .domain import AuditEvent
from .tasks import send_audit_event


async def log(event: AuditEvent) -> None:
    """Dispatch an audit event to RabbitMQ for asynchronous persistence to Postgres.

    Returns as soon as the event is on the queue — the API response is
    never delayed by the database write.
    """
    payload = event.model_dump(mode="json")
    await send_audit_event.kiq(payload)
