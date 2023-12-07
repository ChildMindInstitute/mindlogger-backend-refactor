import asyncio

from fastapi import Query
from fastapi.responses import Response
from starlette import status


def readiness():
    return Response("Readiness - OK!")


def liveness():
    return Response("Liveness - OK!")


statuses = {
    code for var, code in vars(status).items() if var.startswith("HTTP_")
}
exclude = {301, 302}
supported_statuses = statuses - exclude


async def statuscode(
    code: int = 200, timeout: float = Query(0.0, ge=0.0, le=60.0)
):
    if code not in supported_statuses:
        return Response("Wrong status code", status_code=400)
    await asyncio.sleep(timeout)
    return Response(status_code=code)
