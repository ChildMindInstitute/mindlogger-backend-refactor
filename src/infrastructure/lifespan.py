from fastapi import FastAPI

from broker import broker
from infrastructure.logger import logger


async def startup_taskiq() -> None:
    if not broker.is_worker_process:
        logger.info("Broker startup")
        await broker.startup()


async def shutdown_taskiq() -> None:
    if not broker.is_worker_process:
        logger.info("Broker shutdown")
        await broker.shutdown()


async def startup(app: FastAPI):
    await startup_taskiq()


async def shutdown(app: FastAPI):
    await shutdown_taskiq()
