from contextlib import asynccontextmanager
from typing import AsyncIterator

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await startup_taskiq()
    yield
    await shutdown_taskiq()
