import asyncio

from fastapi import Body, Depends, Query
from fastapi.responses import Response
from starlette import status

from apps.authentication.deps import get_optional_current_user
from apps.healthcheck.domain import AppInfo, EmergencyMessage, EmergencyMessageType
from apps.shared.domain import Response as ResponseModel
from apps.users import User
from config import settings


def readiness():
    return Response("Readiness - OK!")


def liveness():
    return Response("Liveness - OK!")


statuses = {code for var, code in vars(status).items() if var.startswith("HTTP_")}
exclude = {301, 302}
supported_statuses = statuses - exclude


async def statuscode(code: int = 200, timeout: float = Query(0.0, ge=0.0, le=60.0)):
    if code not in supported_statuses:
        return Response("Wrong status code", status_code=400)
    await asyncio.sleep(timeout)
    return Response(status_code=code)


async def emergency_message(
    info: AppInfo = Body(...),
    user: User | None = Depends(get_optional_current_user),
    test: bool = Query(False),
) -> ResponseModel[EmergencyMessage]:
    # Logic to generate response message based on the user info and app os/version

    result = EmergencyMessage()

    if test:
        message = (
            f"User: {user.email_encrypted if user else None}, "
            f"request: {info.json()}, "
            f"test url: [url](https://{settings.service.urls.frontend.web_base})"
        )

        result = EmergencyMessage(message=message, message_type=EmergencyMessageType.blocker, dismissible=False)

    return ResponseModel(result=result)
