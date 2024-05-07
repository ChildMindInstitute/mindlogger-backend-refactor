import datetime
import json
import os
import time
import uuid

import aiohttp

from apps.activities.crud.activity import ActivitiesCRUD
from apps.activities.crud.activity_item import ActivityItemsCRUD
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.errors import ReportServerError
from apps.answers.service import ReportServerService
from apps.applets.crud.applets import AppletsCRUD
from apps.integrations.loris.crud.user_relationship import MlLorisUserRelationshipCRUD
from apps.integrations.loris.db.schemas import MlLorisUserRelationshipSchema
from apps.integrations.loris.domain import MlLorisUserRelationship, UnencryptedApplet
from apps.integrations.loris.errors import LorisServerError, MlLorisUserRelationshipNotFoundError
from apps.users.domain import User
from infrastructure.database.core import atomic
from infrastructure.logger import logger

__all__ = [
    "LorisIntegrationService",
]


VISIT = "V1"

LORIS_LOGIN_URL = "https://loris.cmiml.net/api/v0.0.3/login/"
LORIS_ML_URL = "https://loris.cmiml.net/mindlogger/v1/schema/"
LORIS_CREATE_CANDIDATE = "https://loris.cmiml.net/api/v0.0.3/candidates"
LORIS_CREATE_VISIT = "https://loris.cmiml.net/api/v0.0.3/candidates/{}/{}"
LORIS_START_VISIT = "https://loris.cmiml.net/api/v0.0.4-dev/candidates/{}/{}"
LORIS_ADD_INSTRUMENTS = "https://loris.cmiml.net/api/v0.0.4-dev/candidates/{}/{}/instruments"
LORIS_INSTRUMENT_DATA = "https://loris.cmiml.net/api/v0.0.3/candidates/{}/{}/instruments/{}"

LORIS_USERNAME = os.getenv("LORIS_USERNAME")
LORIS_PASSWORD = os.getenv("LORIS_PASSWORD")

LORIS_LOGIN_DATA = {
    "username": LORIS_USERNAME,
    "password": LORIS_PASSWORD,
}


class LorisIntegrationService:
    def __init__(self, applet_id: uuid.UUID, session, user: User) -> None:
        self.applet_id = applet_id
        self.session = session
        self.user = user

    async def integration(self):
        respondents = await AnswersCRUD(self.session).get_respondents_by_applet_id_and_readiness_to_share_data(
            applet_id=self.applet_id
        )
        if not respondents:
            logger.info(
                f"Do not found any respondents for given applet: \
                    {str(self.applet_id)}. Finish."
            )
            return

        users_answers: dict = {}
        for respondent in set(respondents):
            try:
                report_service = ReportServerService(self.session)
                decrypted_answers: dict[str, list] | None = await report_service.decrypt_data_for_loris(
                    self.applet_id, respondent
                )
                if not decrypted_answers:
                    logger.info("Error during request to report server, no answers")
                    return
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

        applet_crud = AppletsCRUD(self.session)
        applet = await applet_crud.get_by_id(self.applet_id)
        loris_data = {
            "id": self.applet_id,
            "displayName": applet.display_name,
            "description": list(applet.description.values())[0],
            "activities": None,
        }

        answers_for_loris_by_respondent: dict
        activities: list
        activities, answers_for_loris_by_respondent = await self._prepare_activities_and_answers(users_answers)
        loris_data["activities"] = activities
        activities_ids: list = [str(activitie["id"]) for activitie in activities]

        token: str = await self._login_to_loris()
        headers = {
            "Authorization": f"Bearer: {token}",
            "Content-Type": "application/json",
            "accept": "*/*",
        }
        await self._upload_applet_schema_to_loris(loris_data, headers)

        for user, answer in answers_for_loris_by_respondent.items():
            candidate_id: str
            relationship_crud = MlLorisUserRelationshipCRUD(self.session)
            try:
                relationship: MlLorisUserRelationship = await relationship_crud.get_by_ml_user_id(uuid.UUID(user))
                candidate_id = relationship.loris_user_id
            except MlLorisUserRelationshipNotFoundError as e:
                logger.info(f"{e}. Need to create new candidate")
                candidate_id = await self._create_candidate_and_visit(headers, relationship_crud, uuid.UUID(user))

            await self._add_instrument_to_loris(headers, candidate_id, activities_ids)
            await self._add_instrument_data_to_loris(headers, candidate_id, answer, activities_ids)

            logger.info(f"Successfully send data for user: {user}," f" with loris id: {candidate_id}")

        logger.info("All finished")

    async def _prepare_activities_and_answers(self, users_answers: dict) -> tuple[list, dict]:
        activities_crud = ActivitiesCRUD(self.session)
        activities_items_crud = ActivityItemsCRUD(self.session)
        answers_for_loris_by_respondent: dict = {}
        activities: list = []
        applet_activities = await activities_crud.get_by_applet_id(self.applet_id)
        for _activitie in applet_activities:
            items: list = []
            _activities_items = await activities_items_crud.get_by_activity_id(_activitie.id)
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
                    answers_for_loris = await self._ml_answer_to_loris(
                        str(_activitie.id),
                        items,
                        answers[str(_activitie.id)],
                    )
                    if user not in answers_for_loris_by_respondent:
                        answers_for_loris_by_respondent[user] = answers_for_loris
                    else:
                        answers_for_loris_by_respondent[user].update(answers_for_loris)

        return activities, answers_for_loris_by_respondent

    async def _ml_answer_to_loris(self, activitie_id: str, items: list, data: list) -> dict:
        loris_answers: dict = {}

        for i in range(len(items)):
            key: str = "__".join([activitie_id, items[i]["name"]])
            match items[i]["responseType"]:
                case "singleSelect":
                    index = data[i]["value"]
                    _data = items[i]["responseValues"]["options"][index]["text"]
                    loris_answers[key] = _data
                case "multiSelect":
                    loris_answers[key] = list(map(str, data[i]["value"]))
                case "slider":
                    loris_answers[key] = data[i]["value"]
                case "numberSelect":
                    loris_answers[key] = int(data[i]["value"])
                case "text":
                    loris_answers[key] = data[i]
                case "timeRange":
                    _data = data[i]["value"]

                    key_start = key + "__start"
                    key_end = key + "__end"

                    start_hour = _data["from"]["hour"]
                    start_minute = _data["from"]["minute"]

                    end_hour = _data["to"]["hour"]
                    end_minute = _data["to"]["minute"]

                    start = "{:02d}:{:02d}".format(start_hour, start_minute)
                    end = "{:02d}:{:02d}".format(end_hour, end_minute)

                    loris_answers[key_start] = start
                    loris_answers[key_end] = end
                case "geolocation":
                    _data = data[i]["value"]

                    key_latitude = key + "__latitude"
                    key_longitude = key + "__longitude"

                    latitude = str(_data["latitude"])
                    longitude = str(_data["longitude"])

                    loris_answers[key_latitude] = latitude
                    loris_answers[key_longitude] = longitude
                case "date":
                    _data = data[i]["value"]

                    date = "{:04d}-{:02d}-{:02d}".format(_data["year"], _data["month"], _data["day"])

                    loris_answers[key] = date
                case "sliderRows":
                    data = data[i]["value"]

                    for i, v in enumerate(data):
                        _key = key + "__{}".format(i)
                        loris_answers[_key] = v
                case "singleSelectRows":
                    data = data[i]["value"]

                    for i, v in enumerate(data):
                        _key = key + "__{}".format(i)
                        loris_answers[_key] = v
                case "multiSelectRows":
                    data = data[i]["value"]

                    for i, v in enumerate(data):
                        _key = key + "__{}".format(i)
                        loris_answers[_key] = v
                case "time":
                    _data = data[i]["value"]

                    time = "{:02d}:{:02d}".format(_data["hours"], _data["minutes"])

                    loris_answers[key] = time
                case _:
                    logger.info(f"Unknown item type: {items[i]['responseType']}")
                    # raise Exception

        return loris_answers

    async def _login_to_loris(self) -> str:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info(f"Sending LOGIN request to the loris server {LORIS_LOGIN_URL}")
            start = time.time()
            async with session.post(
                LORIS_LOGIN_URL,
                data=json.dumps(LORIS_LOGIN_DATA),
            ) as resp:
                duration = time.time() - start
                if resp.status == 200:
                    logger.info(f"Successful request in {duration:.1f} seconds.")
                    response_data = await resp.json()
                    return response_data["token"]
                else:
                    logger.error(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

    async def _upload_applet_schema_to_loris(self, schema: dict, headers: dict):
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info(f"Sending UPLOAD SCHEMA request to the loris server " f"{LORIS_ML_URL}")
            start = time.time()
            async with session.post(
                LORIS_ML_URL,
                data=UnencryptedApplet(**schema).json(),
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 200:
                    logger.info(f"Successful request in {duration:.1f} seconds.")
                else:
                    logger.error(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

    async def _create_candidate_and_visit(
        self, headers: dict, relationship_crud: MlLorisUserRelationshipCRUD, ml_user_id: uuid.UUID
    ) -> str:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info(f"Sending CREATE CANDIDATE request to the loris server " f"{LORIS_CREATE_CANDIDATE}")
            start = time.time()
            _data_candidate = {
                "Candidate": {
                    "Project": "loris",
                    "Site": "Mindlogger Integration Center",
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
                    logger.info(f"Successful request in {duration:.1f} seconds.")
                    candidate_data = await resp.json()
                    candidate_id = candidate_data["CandID"]
                else:
                    logger.info(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

            async with atomic(relationship_crud.session):
                await relationship_crud.save(
                    MlLorisUserRelationshipSchema(
                        ml_user_uuid=ml_user_id,
                        loris_user_id=candidate_id,
                    )
                )

            logger.info(
                f"Sending CREATE VISIT request to the loris server" f"{LORIS_CREATE_VISIT.format(candidate_id, VISIT)}"
            )
            start = time.time()
            _data_create_visit = {
                "CandID": candidate_id,
                "Visit": VISIT,
                "Site": "Mindlogger Integration Center",
                "Battery": "Control",
                "Project": "loris",
            }
            async with session.put(
                LORIS_CREATE_VISIT.format(candidate_id, VISIT),
                data=json.dumps(_data_create_visit),
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 201:
                    logger.info(f"Successful request in {duration:.1f} seconds.")
                else:
                    logger.info(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

            logger.info(
                f"Sending START VISIT request to the loris server " f"{LORIS_START_VISIT.format(candidate_id, VISIT)}"
            )
            start = time.time()
            _data_start_visit = {
                "CandID": candidate_id,
                "Visit": VISIT,
                "Site": "Mindlogger Integration Center",
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
                LORIS_START_VISIT.format(candidate_id, VISIT),
                data=json.dumps(_data_start_visit),
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 204:
                    logger.info(f"Successful request in {duration:.1f} seconds.")
                else:
                    logger.info(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

        return candidate_id

    async def _add_instrument_to_loris(self, headers: dict, candidate_id: str, activities_ids: list):
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info(
                f"Sending ADD INSTRUMENTS request to the loris server "
                f"{LORIS_ADD_INSTRUMENTS.format(candidate_id, VISIT)}"
            )
            start = time.time()
            _data_add_instruments = {
                "Meta": {
                    "Candidate": candidate_id,
                    "Visit": VISIT,
                },
                "Instruments": activities_ids,
            }
            async with session.post(
                LORIS_ADD_INSTRUMENTS.format(candidate_id, VISIT),
                data=json.dumps(_data_add_instruments),
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 200:
                    logger.info(f"Successful request in {duration:.1f} seconds.")
                else:
                    logger.info(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    logger.info(f"response is: " f"{error_message}\nstatus is: {resp.status}")
                    raise LorisServerError(message=error_message)

    async def _add_instrument_data_to_loris(self, headers: dict, candidate_id: str, answer: dict, activities_ids: list):
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for activitie_id in activities_ids:
                logger.info(
                    f"Sending SEND INSTUMENT DATA request to the loris server "
                    f"{LORIS_INSTRUMENT_DATA.format(candidate_id, VISIT, activitie_id)}"
                )
                start = time.time()
                _data_instrument_data = {
                    "Meta": {
                        "Instrument": activitie_id,
                        "Visit": VISIT,
                        "Candidate": candidate_id,
                        "DDE": True,
                    },
                    activitie_id: answer,
                }
                logger.info(f"Sending SEND INSTUMENT DATA is : {json.dumps(_data_instrument_data)} ")
                async with session.put(
                    LORIS_INSTRUMENT_DATA.format(candidate_id, VISIT, activitie_id),
                    data=json.dumps(_data_instrument_data),
                    headers=headers,
                ) as resp:
                    duration = time.time() - start
                    if resp.status == 204:
                        logger.info(f"Successful request in {duration:.1f} seconds.")
                    else:
                        logger.info(f"Failed request in {duration:.1f} seconds.")
                        error_message = await resp.text()
                        logger.info(f"response is: " f"{error_message}\nstatus is: {resp.status}")
                        raise LorisServerError(message=error_message)
