import datetime
import itertools
import json
import time
import uuid

import aiohttp
from pydantic.json import pydantic_encoder

from apps.activities.crud.activity_history import ActivityHistoriesCRUD
from apps.activities.crud.activity_item_history import ActivityItemHistoriesCRUD
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.errors import ReportServerError
from apps.answers.service import ReportServerService
from apps.applets.crud.applets_history import AppletHistoriesCRUD
from apps.integrations.loris.crud.user_relationship import MlLorisUserRelationshipCRUD
from apps.integrations.loris.db.schemas import MlLorisUserRelationshipSchema
from apps.integrations.loris.domain import MlLorisUserRelationship, UnencryptedAppletVersion
from apps.integrations.loris.errors import LorisServerError, MlLorisUserRelationshipNotFoundError
from apps.users.domain import User
from config import settings
from infrastructure.database.core import atomic
from infrastructure.logger import logger

__all__ = [
    "LorisIntegrationService",
]


VISIT = "V1"

LORIS_LOGIN_DATA = {
    "username": settings.loris.username,
    "password": settings.loris.password,
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
                f"No respondents found for given applet: \
                    {str(self.applet_id)}. End of the synchronization."
            )
            return

        users_answers: dict = {}
        answer_versions: list = []
        for respondent in set(respondents):
            try:
                report_service = ReportServerService(self.session)
                decrypted_answers_and_versions: tuple[dict, list] | None = await report_service.decrypt_data_for_loris(
                    self.applet_id, respondent
                )
                if not decrypted_answers_and_versions:
                    logger.info("Error during request to report server, no answers")
                    return
                decrypted_answers: dict[str, list] = decrypted_answers_and_versions[0]
                answer_versions = decrypted_answers_and_versions[1]
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

        token: str = await self._login_to_loris()
        headers = {
            "Authorization": f"Bearer: {token}",
            "Content-Type": "application/json",
            "accept": "*/*",
        }

        # check loris for already existing versions of the applet
        existing_versions = await self._get_existing_versions_from_loris(self.applet_id, headers)
        answer_versions = list(set(answer_versions))

        missing_applet_versions = list(set(answer_versions) - set(existing_versions))
        # get missing versions of the applet
        applet_history_crud = AppletHistoriesCRUD(self.session)

        loris_data = []

        for version in missing_applet_versions:
            applet_version = await applet_history_crud.retrieve_by_applet_version(f"{str(self.applet_id)}_{version}")
            loris_data.append(
                {
                    "version": version,
                    "applet": {
                        "id": self.applet_id,
                        "displayName": applet_version.display_name,
                        "description": list(applet_version.description.values())[0],
                        "activities": None,
                    },
                }
            )

        answers_for_loris_by_respondent: dict

        activities_by_versions = await self._prepare_activities(answer_versions)
        for loris_datum in loris_data:
            loris_datum["applet"]["activities"] = activities_by_versions[loris_datum["version"]]

        activities_map = {
            activity["id"]: activity
            for activity in list(itertools.chain.from_iterable(list(activities_by_versions.values())))
        }

        answers_for_loris_by_respondent = await self._prepare_answers(users_answers, activities_map)

        activities_ids: list = list(activities_map.keys())
        if loris_data:
            await self._upload_applet_schema_to_loris(loris_data, headers)

        # check loris for already existing answers of the applet and filter them out
        existing_answers = await self._get_existing_answers_from_loris(self.applet_id, headers)

        for user, answer in answers_for_loris_by_respondent.items():
            candidate_id: str
            relationship_crud = MlLorisUserRelationshipCRUD(self.session)
            try:
                relationship: MlLorisUserRelationship = await relationship_crud.get_by_ml_user_id(uuid.UUID(user))
                candidate_id = relationship.loris_user_id
            except MlLorisUserRelationshipNotFoundError as e:
                logger.info(f"{e}. Need to create new candidate")
                candidate_id = await self._create_candidate_and_visit(headers, relationship_crud, uuid.UUID(user))
            filtered_answers = {
                key: value for key, value in answer.items() if key.split("__")[2] not in existing_answers
            }
            if filtered_answers:
                await self._add_instrument_to_loris(headers, candidate_id, activities_ids)
                await self._add_instrument_data_to_loris(headers, candidate_id, filtered_answers, activities_ids)

            logger.info(f"Successfully send data for user: {user}," f" with loris id: {candidate_id}")

        logger.info("All finished")

    async def _prepare_activities(self, versions: list) -> dict:
        activity_history_crud = ActivityHistoriesCRUD(self.session)
        activities_items_history_crud = ActivityItemHistoriesCRUD(self.session)
        activities_by_versions: dict = {}
        for version in versions:
            applet_activities = await activity_history_crud.get_by_applet_id_version(f"{str(self.applet_id)}_{version}")
            activities: list = []
            for _activitie in applet_activities:
                items: list = []
                _activities_items = await activities_items_history_crud.get_by_activity_id_version(
                    _activitie.id_version
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
                        "id": str(_activitie.id_version).replace("_", "__"),
                        "name": _activitie.name,
                        "description": list(_activitie.description.values())[0],
                        "splash_screen": _activitie.splash_screen,
                        "image": _activitie.image,
                        "order": _activitie.order,
                        "createdAt": _activitie.created_at,
                        "items": items,
                    }
                )
            activities_by_versions[version] = activities

        return activities_by_versions

    async def _prepare_answers(self, users_answers: dict, activities: dict):
        answers_for_loris_by_respondent: dict = {}
        for user, answers in users_answers.items():
            for id, answer in answers.items():
                activity_id, version, answer_id = id.split("__")
                activity_version_id = f"{activity_id}__{version}"
                if activity_version_id in activities:
                    answers_for_loris = await self._ml_answer_to_loris(
                        answer_id,
                        activity_id,
                        version,
                        activities[activity_version_id]["items"],
                        answer,
                    )
                    if user not in answers_for_loris_by_respondent:
                        answers_for_loris_by_respondent[user] = answers_for_loris
                    else:
                        answers_for_loris_by_respondent[user].update(answers_for_loris)
        return answers_for_loris_by_respondent

    async def _ml_answer_to_loris(
        self, answer_id: str, activity_id: str, version: str, items: list, data: list
    ) -> dict:
        loris_answers: dict = {}

        for i in range(len(items)):
            key: str = "__".join([activity_id, version, answer_id, items[i]["name"]])
            match items[i]["responseType"]:
                case "singleSelect":
                    index = data[i]["value"]
                    _data = items[i]["responseValues"]["options"][index]["text"]
                    loris_answers[key] = _data
                case "multiSelect":
                    _data = data[i]["value"]
                    loris_answers[key] = [items[i]["responseValues"]["options"][i_]["text"] for i_ in _data]
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
                    _data = data[i]["value"]

                    for i, v in enumerate(_data):
                        _key = key + "__{}".format(i)
                        loris_answers[_key] = v
                case "singleSelectRows":
                    _data = data[i]["value"]

                    for i, v in enumerate(_data):
                        _key = key + "__{}".format(i)
                        loris_answers[_key] = v
                case "multiSelectRows":
                    _data = data[i]["value"]

                    for i, v in enumerate(_data):
                        _key = key + "__{}".format(i)
                        loris_answers[_key] = [answer for answer in v if answer is not None]
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
            logger.info(f"Sending LOGIN request to the loris server {settings.loris.login_url}")
            start = time.time()
            async with session.post(
                settings.loris.login_url,
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

    async def _get_existing_versions_from_loris(self, applet_id: str, headers: dict) -> str:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = settings.loris.ml_schema_existing_versions_url.format(self.applet_id)
            logger.info(f"Sending EXISTING SCHEMA VERSIONS request to the loris server {url}")
            start = time.time()
            async with session.get(
                url,
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 200:
                    logger.info(f"Successful request in {duration:.1f} seconds.")
                    response_data = await resp.json()
                    return response_data
                else:
                    logger.error(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

    async def _get_existing_answers_from_loris(self, applet_id: str, headers: dict) -> str:
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            url = settings.loris.ml_schema_existing_answers_url.format(self.applet_id)
            logger.info(f"Sending EXISTING ANSWERS request to the loris server {url}")
            start = time.time()
            async with session.get(
                url,
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 200:
                    logger.info(f"Successful request in {duration:.1f} seconds.")
                    response_data = await resp.json()
                    return response_data
                else:
                    logger.error(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

    async def _upload_applet_schema_to_loris(self, schemas: list, headers: dict):
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info(f"Sending UPLOAD SCHEMA request to the loris server {settings.loris.ml_schema_url}")
            start = time.time()
            async with session.post(
                settings.loris.ml_schema_url,
                data=json.dumps([UnencryptedAppletVersion(**schema) for schema in schemas], default=pydantic_encoder),
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
            logger.info(f"Sending CREATE CANDIDATE request to the loris server {settings.loris.create_candidate_url}")
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
                settings.loris.create_candidate_url,
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

            create_visit_url: str = settings.loris.create_visit_url.format(candidate_id, VISIT)
            logger.info(f"Sending CREATE VISIT request to the loris server {create_visit_url}")
            start = time.time()
            _data_create_visit = {
                "CandID": candidate_id,
                "Visit": VISIT,
                "Site": "Mindlogger Integration Center",
                "Battery": "Control",
                "Project": "loris",
            }
            async with session.put(
                settings.loris.create_visit_url.format(candidate_id, VISIT),
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

            start_visit_url: str = settings.loris.start_visit_url.format(candidate_id, VISIT)
            logger.info(f"Sending START VISIT request to the loris server {start_visit_url}")
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
                settings.loris.start_visit_url.format(candidate_id, VISIT),
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
                f"{settings.loris.add_instruments_url.format(candidate_id, VISIT)}"
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
                settings.loris.add_instruments_url.format(candidate_id, VISIT),
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
            for activity_id in activities_ids:
                answer_by_activity_id = {key: value for key, value in answer.items() if activity_id in key}
                if answer_by_activity_id:
                    logger.info(
                        f"Sending SEND INSTUMENT DATA request to the loris server "
                        f"{settings.loris.instrument_data_url.format(candidate_id, VISIT, activity_id)}"
                    )
                    start = time.time()
                    _data_instrument_data = {
                        "Meta": {
                            "Instrument": activity_id,
                            "Visit": VISIT,
                            "Candidate": candidate_id,
                            "DDE": True,
                        },
                        activity_id: answer_by_activity_id,
                    }
                    logger.info(f"Sending SEND INSTUMENT DATA is : {json.dumps(_data_instrument_data)} ")
                    async with session.put(
                        settings.loris.instrument_data_url.format(candidate_id, VISIT, activity_id),
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
