from infrastructure.logger import logger

from .domain import AuditEvent


async def log(event: AuditEvent) -> None:
    payload = event.model_dump(by_alias=True, mode="json")
    logger.info("audit_event", **payload)  # TODO: Replace with sending event to RabbitMQ/OpenSearch.
