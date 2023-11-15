import uuid
import time

import aiohttp

from fastapi import Body, Depends
from starlette import status
from starlette.responses import Response as HTTPResponse

from apps.integrations.loris.domain import (
    UnencryptedApplet,
    LorisServerResponse,
)
from apps.integrations.loris.errors import LorisServerError

from apps.applets.filters import AppletQueryParams
from apps.applets.service import AppletHistoryService, AppletService
from apps.authentication.deps import get_current_user
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.shared.domain.response import Response
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database import atomic
from infrastructure.database.deps import get_session

__all__ = [
    "send_applet_data_to_loris",
]

from infrastructure.logger import logger


# TODO move to env and config
LORIS_URL = "localhost/mindlogger/applet_data"


async def send_applet_data_to_loris(
    applet_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: UnencryptedApplet = Body(...),
    session=Depends(get_session),
    # ) -> Response:
):
    async with aiohttp.ClientSession() as session:
        logger.info(f"Sending request to the loris server {LORIS_URL}.")
        start = time.time()
        async with session.post(
            LORIS_URL,
            json=dict(payload=schema),
        ) as resp:
            duration = time.time() - start
            if resp.status == 200:
                logger.info(f"Successful request in {duration:.1f} seconds.")
                response_data = await resp.json()
                return LorisServerResponse(**response_data)
            else:
                logger.error(f"Failed request in {duration:.1f} seconds.")
                error_message = await resp.text()
                raise LorisServerError(message=error_message)
    # return Response()
    # return status.HTTP_202_ACCEPTED
