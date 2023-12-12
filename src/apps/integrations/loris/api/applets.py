import time
import uuid

import aiohttp
from fastapi import Body, Depends, BackgroundTasks

from apps.authentication.deps import get_current_user
from apps.integrations.loris.domain import (
    LorisServerResponse,
    UnencryptedApplet,
)
from apps.integrations.loris.errors import LorisServerError

from apps.shared.domain.response import Response
from apps.users.domain import User
from infrastructure.database.deps import get_session
from infrastructure.logger import logger

from starlette import status
from starlette.responses import Response as HTTPResponse


__all__ = [
    "start_transmit_process",
]


# TODO move to env and config
LORIS_URL = "localhost/mindlogger/applet_data"


def integration(applet_id: uuid.UUID):
    print("start backgroud task")
    time.sleep(10)
    print(f"end backgroud task. applet id is: {applet_id}")


async def start_transmit_process(
    applet_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    # user: User = Depends(get_current_user),
    session=Depends(get_session),
    # ) -> Response:
):
    # async with aiohttp.ClientSession() as session:
    #     logger.info(f"Sending request to the loris server {LORIS_URL}.")
    #     start = time.time()
    #     async with session.post(
    #         LORIS_URL,
    #         json=dict(payload=schema),
    #     ) as resp:
    #         duration = time.time() - start
    #         if resp.status == 200:
    #             logger.info(f"Successful request in {duration:.1f} seconds.")
    #             response_data = await resp.json()
    #             return LorisServerResponse(**response_data)
    #         else:
    #             logger.error(f"Failed request in {duration:.1f} seconds.")
    #             error_message = await resp.text()
    #             raise LorisServerError(message=error_message)

    background_tasks.add_task(integration, applet_id)
    return HTTPResponse(status_code=status.HTTP_202_ACCEPTED)
