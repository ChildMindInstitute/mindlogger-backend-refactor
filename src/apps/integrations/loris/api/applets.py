import json
import time
import uuid

import aiohttp
from fastapi import BackgroundTasks, Depends
from starlette import status
from starlette.responses import Response as HTTPResponse

from apps.activities.crud.activity import ActivitiesCRUD
from apps.activities.crud.activity_item import ActivityItemsCRUD
from apps.answers.errors import ReportServerError
from apps.answers.service import ReportServerService
from apps.applets.crud.applets import AppletsCRUD
from apps.authentication.deps import get_current_user
from apps.integrations.loris.domain import (
    LorisServerResponse,
    UnencryptedApplet,
)
from apps.integrations.loris.errors import LorisServerError
from apps.users.domain import User
from infrastructure.database.deps import get_session
from infrastructure.logger import logger

__all__ = [
    "start_transmit_process",
]


# TODO move to env and config
LORIS_LOGIN_URL = "https://loris.cmiml.net/api/v0.0.3/login/"
LORIS_ML_URL = "https://loris.cmiml.net/mindlogger/v1/schema/"

LORIS_USERNAME = "lorisfrontadmin"
LORIS_PASSWORD = "2eN5i4gmbWpDQb08"

LORIS_LOGIN_DATA = {
    "username": LORIS_USERNAME,
    "password": LORIS_PASSWORD,
}


async def integration(applet_id: uuid.UUID, session):
    try:
        report_service = ReportServerService(session)
        decrypted_answers = await report_service.decrypt_data_for_loris(
            applet_id
        )
        # logger.info(f"decrypted_answers: {decrypted_answers}")
    except ReportServerError as e:
        logger.info(f"error during request to report server: {e}")
        return

    activities_crud = ActivitiesCRUD(session)
    activities_items_crud = ActivityItemsCRUD(session)
    applet_crud = AppletsCRUD(session)

    applet = await applet_crud.get_by_id(applet_id)

    loris_data = {
        "id": applet_id,
        "displayName": applet.display_name,
        "description": list(applet.description.values())[0],
        "activities": None,
    }
    activities: list = []
    for activitie in decrypted_answers["result"]:
        items: list = []
        act_id = activitie["activityId"]
        _activitie = await activities_crud.get_by_applet_id_and_activity_id(
            applet_id, uuid.UUID(act_id)
        )
        _activities_items = await activities_items_crud.get_by_activity_id(
            uuid.UUID(act_id)
        )
        for item in _activities_items:
            items.append(
                {
                    "id": item.id,
                    "question": list(item.question.values())[0],
                    "responseType": item.response_type,
                    "responseValues": item.response_values,
                    "config": item.config,
                    "name": item.name,
                    "isHidden": item.is_hidden,
                    "conditionalLogic": item.conditional_logic,
                    "allowEdit": item.allow_edit,
                }
            )
        activities.append(
            {
                "id": _activitie.id,
                "name": _activitie.name,
                "description": list(_activitie.description.values())[0],
                "splash_screen": _activitie.splash_screen,
                "image": _activitie.image,
                "order": _activitie.order,
                "createdAt": _activitie.created_at,
                "items": items,
                "results": activitie["data"],
            }
        )
    loris_data["activities"] = activities
    # logger.info(f"loris_data: {loris_data}")

    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        logger.info(
            f"Sending LOGIN request to the loris server {LORIS_LOGIN_URL}."
        )
        start = time.time()
        async with session.post(
            LORIS_LOGIN_URL,
            data=json.dumps(LORIS_LOGIN_DATA),
        ) as resp:
            duration = time.time() - start
            if resp.status == 200:
                logger.info(f"Successful request in {duration:.1f} seconds.")
                response_data = await resp.json()
                # return LorisServerResponse(**response_data)
            else:
                logger.error(f"Failed request in {duration:.1f} seconds.")
                error_message = await resp.text()
                raise LorisServerError(message=error_message)

        logger.info(
            f"Sending UPLOAD DATA request to the loris server {LORIS_ML_URL}."
        )
        headers = {"Authorization": f"Bearer: {response_data['token']}"}
        start = time.time()
        async with session.post(
            LORIS_ML_URL,
            data=UnencryptedApplet(**loris_data).json(),
            headers=headers,
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


async def start_transmit_process(
    applet_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    # ) -> Response:
):
    background_tasks.add_task(integration, applet_id, session)
    return HTTPResponse(status_code=status.HTTP_202_ACCEPTED)
