import datetime
import json
import time
import uuid

import aiohttp
from fastapi import BackgroundTasks, Depends
from starlette import status
from starlette.responses import Response as HTTPResponse

from apps.activities.crud.activity import ActivitiesCRUD
from apps.activities.crud.activity_item import ActivityItemsCRUD
from apps.answers.crud.answers import AnswersCRUD
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
VISIT = "V1"

LORIS_LOGIN_URL = "https://loris.cmiml.net/api/v0.0.3/login/"
LORIS_ML_URL = "https://loris.cmiml.net/mindlogger/v1/schema/"
LORIS_CREATE_CANDIDATE = "https://loris.cmiml.net/api/v0.0.3/candidates"
LORIS_CREATE_VISIT = "https://loris.cmiml.net/api/v0.0.3/candidates/{}/{}"
LORIS_START_VISIT = "https://loris.cmiml.net/api/v0.0.4-dev/candidates/{}/{}"
LORIS_INSTRUMENT_DATA = (
    "https://loris.cmiml.net/api/v0.0.3/candidates/{}/{}/instruments/{}"
)

LORIS_USERNAME = "lorisfrontadmin"
LORIS_PASSWORD = "2eN5i4gmbWpDQb08"

LORIS_LOGIN_DATA = {
    "username": LORIS_USERNAME,
    "password": LORIS_PASSWORD,
}


async def integration(applet_id: uuid.UUID, session):
    respondents = await AnswersCRUD(
        session
    ).get_respondents_by_applet_id_and_readiness_to_share_data(
        applet_id=applet_id
    )
    if not respondents:
        logger.info(
            f"Do not found any respondents for given applet: \
                {str(applet_id)}. Finish."
        )
        return

    users_answers: dict = {}
    for respondent in set(respondents):
        try:
            report_service = ReportServerService(session)
            decrypted_answers = await report_service.decrypt_data_for_loris(
                applet_id, respondent
            )
            _result_dict = {}
            for item in decrypted_answers["result"]:
                activity_id = item["activityId"]
                data_info = item["data"]

                if not data_info:
                    continue

                _result_dict[activity_id] = data_info
            users_answers[str(respondent)] = _result_dict
            # logger.info(f"Decrypted_answers for {respondent}: \
            #             {json.dumps(decrypted_answers)}")
        except ReportServerError as e:
            logger.info(f"Error during request to report server: {e}")
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

    answers_for_loris_by_respondent: dict = {}
    activities: list = []
    applet_activities = await activities_crud.get_by_applet_id(applet_id)
    for _activitie in applet_activities:
        items: list = []
        _activities_items = await activities_items_crud.get_by_activity_id(
            _activitie.id
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
            }
        )
        for user, answers in users_answers.items():
            if str(_activitie.id) in answers:
                answers_for_loris = await ml_answer_to_loris(
                    str(applet_id),
                    str(_activitie.id),
                    items,
                    answers[str(_activitie.id)],
                )
                if user not in answers_for_loris_by_respondent:
                    answers_for_loris_by_respondent[user] = answers_for_loris
                else:
                    answers_for_loris_by_respondent[user].update(
                        answers_for_loris
                    )
    loris_data["activities"] = activities

    timeout = aiohttp.ClientTimeout(total=60)
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
            else:
                logger.error(f"Failed request in {duration:.1f} seconds.")
                error_message = await resp.text()
                raise LorisServerError(message=error_message)

        headers = {
            "Authorization": f"Bearer: {response_data['token']}",
            "Content-Type": "application/json",
            "accept": "*/*",
        }
        # logger.info(
        #     f"Sending UPLOAD SCHEMA request to the loris server \
        #         {LORIS_ML_URL}."
        # )
        # start = time.time()
        # async with session.post(
        #     LORIS_ML_URL,
        #     data=UnencryptedApplet(**loris_data).json(),
        #     headers=headers,
        # ) as resp:
        #     duration = time.time() - start
        #     if resp.status == 200:
        #         logger.info(f"Successful request in {duration:.1f} seconds.")
        #         response_data = await resp.json()
        #     else:
        #         logger.error(f"Failed request in {duration:.1f} seconds.")
        #         error_message = await resp.text()
        #         raise LorisServerError(message=error_message)

        # logger.info("On 30 sec pause")
        # time.sleep(30)

        for user, answer in answers_for_loris_by_respondent.items():
            logger.info(
                f"Sending CREATE CANDIDATE request to the loris server \
                    {LORIS_CREATE_CANDIDATE}."
            )
            start = time.time()
            _data_candidate = {
                "Candidate": {
                    "Project": "loris",
                    "Site": "Data Coordinating Center",
                    "DoB": "1970-01-01",
                    "Sex": "Other",
                }
            }
            async with session.post(
                LORIS_CREATE_CANDIDATE,
                data=json.dumps(_data_candidate),
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 201:
                    logger.info(
                        f"Successful request in {duration:.1f} seconds."
                    )
                    candidate_data = await resp.json()
                else:
                    logger.info(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

            logger.info(
                f"Sending CREATE VISIT request to the loris server \
                    {LORIS_CREATE_VISIT.format(candidate_data['CandID'], VISIT)}."
            )
            start = time.time()
            _data_create_visit = {
                "CandID": candidate_data["CandID"],
                "Visit": VISIT,
                "Site": "Data Coordinating Center",
                "Battery": "Control",
                "Project": "loris",
            }
            async with session.put(
                LORIS_CREATE_VISIT.format(candidate_data["CandID"], VISIT),
                data=json.dumps(_data_create_visit),
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 201:
                    logger.info(
                        f"Successful request in {duration:.1f} seconds."
                    )
                else:
                    logger.info(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

            logger.info(
                f"Sending START VISIT request to the loris server \
                    {LORIS_START_VISIT.format(candidate_data['CandID'], VISIT)}."
            )
            start = time.time()
            _data_start_visit = {
                "CandID": candidate_data["CandID"],
                "Visit": VISIT,
                "Site": "Data Coordinating Center",
                "Battery": "Control",
                "Project": "loris",
                "Cohort": "Control",
                "Stages": {
                    "Visit": {
                        "Date": str(datetime.date.today()),
                        "Status": "In Progress",
                    }
                },
            }
            async with session.patch(
                LORIS_START_VISIT.format(candidate_data["CandID"], VISIT),
                data=json.dumps(_data_start_visit),
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 204:
                    logger.info(
                        f"Successful request in {duration:.1f} seconds."
                    )
                else:
                    logger.info(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

            logger.info(
                f"Sending SEND INSTUMENT DATA request to the loris server \
                    {LORIS_INSTRUMENT_DATA.format(candidate_data['CandID'], VISIT, str(applet_id))}."
            )
            start = time.time()
            _data_instrument_data = {
                "Meta": {
                    "Instrument": str(applet_id),
                    "Visit": VISIT,
                    "Candidate": candidate_data["CandID"],
                    "DDE": True,
                },
                str(applet_id): answer,
            }
            async with session.put(
                LORIS_INSTRUMENT_DATA.format(
                    candidate_data["CandID"], VISIT, str(applet_id)
                ),
                data=json.dumps(_data_instrument_data),
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 204:
                    logger.info(
                        f"Successful request in {duration:.1f} seconds."
                    )
                else:
                    logger.info(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    logger.info(
                        f"response is: \
                            {error_message}\nstatus is: {resp.status}"
                    )
                    raise LorisServerError(message=error_message)

            logger.info(
                f"Successfully send data for user: {user},\
                      with loris id: {candidate_data['CandID']}"
            )

    logger.info("All finished")


async def start_transmit_process(
    applet_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
    # ) -> Response:
):
    background_tasks.add_task(integration, applet_id, session)
    return HTTPResponse(status_code=status.HTTP_202_ACCEPTED)


async def ml_answer_to_loris(
    applet_id: str, activitie_id: str, items: list, data: list
) -> dict:
    loris_answers: dict = {}

    for i in range(len(items)):
        key: str = "__".join([applet_id, activitie_id, items[i]["name"]])
        match items[i]["responseType"]:
            case "singleSelect":
                loris_answers[key] = str(data[i]["value"])
            case "multiSelect":
                loris_answers[key] = list(map(str, data[i]["value"]))
            case "slider":
                loris_answers[key] = data[i]["value"]
            case "text":
                loris_answers[key] = data[i]
            case _:
                logger.info(f"Unknown item type: {items[i]['responseType']}")
                # raise Exception

    return loris_answers
