from fastapi import FastAPI

from apps.audit.index_mapping import AUDIT_LOG_MAPPING
from broker import broker
from config import settings
from infrastructure.logger import logger
from infrastructure.utility.opensearch_client import OpenSearchClient


async def startup_taskiq() -> None:
    if not broker.is_worker_process:
        logger.info("Broker startup")
        await broker.startup()


async def shutdown_taskiq() -> None:
    if not broker.is_worker_process:
        logger.info("Broker shutdown")
        await broker.shutdown()


async def startup_opensearch() -> None:
    logger.info("OpenSearch index ensure", index=settings.opensearch.audit_index)
    await OpenSearchClient().ensure_index(settings.opensearch.audit_index, AUDIT_LOG_MAPPING)


async def shutdown_opensearch() -> None:
    await OpenSearchClient().close()



def startup(app: FastAPI):
    async def _startup():
        await startup_taskiq()
        await startup_opensearch()

    return _startup


def shutdown(app: FastAPI):
    async def _shutdown():
        await shutdown_taskiq()
        await shutdown_opensearch()

    return _shutdown
