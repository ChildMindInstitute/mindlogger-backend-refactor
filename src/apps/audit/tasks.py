from broker import broker
from config import settings
from infrastructure.logger import logger
from infrastructure.utility.opensearch_client import OpenSearchClient


@broker.task()
async def send_audit_event(payload: dict, retries: int = 3) -> None:
    """Index an audit event into OpenSearch.

    Retries on failure with a 5s delay; on final failure logs the payload
    so it is captured by the structured log pipeline (Datadog) instead of
    being silently dropped.
    """
    try:
        doc_id = str(payload["event.id"]) if payload.get("event.id") else None
        await OpenSearchClient().index_document(settings.opensearch.audit_index, payload, id=doc_id)
    except Exception as e:
        if retries > 0:
            logger.warning("audit_event_retry", retries_left=retries, error=str(e))
            await send_audit_event.kicker().with_labels(delay=5).kiq(payload, retries=retries - 1)
            return
        logger.error("audit_event_dropped", error=str(e), **payload)
        raise
