from fastapi import FastAPI

from broker import broker


async def startup_taskiq() -> None:
    if not broker.is_worker_process:
        print("Broker startup")
        await broker.startup()


async def shutdown_taskiq() -> None:
    if not broker.is_worker_process:
        print("Broker shutdown")
        await broker.shutdown()


def startup(app: FastAPI):
    async def _startup():
        await startup_taskiq()

    return _startup


def shutdown(app: FastAPI):
    async def _shutdown():
        await shutdown_taskiq()

    return _shutdown
