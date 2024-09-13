import asyncio
import datetime
import itertools
import json
import time
import uuid
from collections import defaultdict

import aiohttp
import sentry_sdk
from pydantic.json import pydantic_encoder

from apps.activities.crud.activity_history import ActivityHistoriesCRUD
from apps.activities.crud.activity_item_history import ActivityItemHistoriesCRUD
from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.db.schemas import AlertSchema
from apps.alerts.domain import AlertMessage, AlertTypes
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.errors import ReportServerError
from apps.answers.service import ReportServerService
from apps.applets.crud.applets_history import AppletHistoriesCRUD
from apps.integrations.crud.integrations import IntegrationsCRUD, IntegrationsSchema
from apps.integrations.domain import AvailableIntegrations
from apps.integrations.loris.crud.user_relationship import MlLorisUserRelationshipCRUD
from apps.integrations.loris.db.schemas import MlLorisUserRelationshipSchema
from apps.integrations.loris.domain.domain import (
    AnswerData,
    LorisIntegrationAlertMessages,
    MlLorisUserRelationship,
    UnencryptedAppletVersion,
    UploadableAnswersData,
    UserVisits,
)
from apps.integrations.loris.domain.loris_integrations import LorisIntegration, LorisIntegrationPublic
from apps.integrations.loris.domain.loris_projects import LorisProjects
from apps.integrations.loris.errors import LorisServerError
from apps.integrations.loris.service.loris_client import LorisClient
from apps.subjects.crud import SubjectsCrud
from apps.users.domain import User
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from config import settings
from infrastructure.database.core import atomic
from infrastructure.database.mixins import HistoryAware
from infrastructure.logger import logger
from infrastructure.utility import RedisCache

__all__ = [
    "LorisIntegrationService",
]


LORIS_LOGIN_DATA = {
    "username": settings.loris.username,
    "password": settings.loris.password,
}


class LorisIntegrationService:
    def __init__(self, applet_id: uuid.UUID, session, user: User, answer_session=None) -> None:
        self.applet_id = applet_id
        self.session = session
        self.user = user
        self.type = AvailableIntegrations.LORIS
        self._answer_session = answer_session

    @property
    def answer_session(self):
        return self._answer_session if self._answer_session else self.session

    async def integration(self, users_and_visits):
        respondents: list = [user.user_id for user in users_and_visits]
        if not respondents:
            await self._create_integration_alerts(
                self.applet_id, message=LorisIntegrationAlertMessages.NO_RESPONDENT.value
            )
            logger.info(
                f"No respondents found for given applet: \
                    {str(self.applet_id)}. End of the synchronization."
            )
            return

        users_answers: dict = {}
        answer_versions: list = []
        for respondent in set(respondents):
            answer_ids = [
                activity.answer_id
                for user in users_and_visits
                if user.user_id == respondent
                for activity in user.activities
            ]
            try:
                report_service = ReportServerService(self.session)
                decrypted_answers_and_versions: tuple[dict, list] | None = await report_service.decrypt_data_for_loris(
                    self.applet_id, respondent, answer_ids
                )
                if not decrypted_answers_and_versions:
                    await self._create_integration_alerts(
                        self.applet_id, message=LorisIntegrationAlertMessages.REPORT_SERVER.value
                    )
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
                await self._create_integration_alerts(
                    self.applet_id, message=LorisIntegrationAlertMessages.REPORT_SERVER.value
                )
                logger.info(f"Error during request to report server: {e}")
                return

        try:
            token: str = await self._login_to_loris()
        except Exception as e:
            await self._create_integration_alerts(
                self.applet_id, message=LorisIntegrationAlertMessages.LORIS_LOGIN_ERROR.value
            )
            raise e

        headers = {
            "Authorization": f"Bearer: {token}",
            "Content-Type": "application/json",
            "accept": "*/*",
        }

        # check loris for already existing versions of the applet
        existing_versions = await self._get_existing_versions_from_loris(headers)

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
        users_and_visits = await self._transform_users_and_visits(users_and_visits, answers_for_loris_by_respondent)
        activities_map = await self._clear_activities_map(activities_map, users_and_visits)

        activities_ids: list = list(activities_map.keys())
        if loris_data:
            await self._upload_applet_schema_to_loris(loris_data, headers)

        # check loris for already existing answers of the applet and filter them out
        existing_answers = await self._get_existing_answers_from_loris(self.applet_id, headers)

        for user, answer in answers_for_loris_by_respondent.items():
            candidate_id: str
            relationship_crud = MlLorisUserRelationshipCRUD(self.session)
            relationships: list[MlLorisUserRelationship] = await relationship_crud.get_by_ml_user_ids([uuid.UUID(user)])
            if not relationships:
                logger.info(f"No such user relationship with ml_user_uuid={user}. Need to create new candidate")
                candidate_id = await self._create_candidate(headers, relationship_crud, uuid.UUID(user))
            else:
                candidate_id = relationships[0].loris_user_id

            _visits_for_user: list[str] = list(users_and_visits[user].values())
            await self._create_and_start_visits(headers, candidate_id, _visits_for_user)
            filtered_answers = {
                key: value for key, value in answer.items() if key.split("__")[2] not in existing_answers
            }
            if filtered_answers:
                await self._add_instrument_to_loris(headers, candidate_id, activities_ids, users_and_visits[user])
                await self._add_instrument_data_to_loris(
                    headers, candidate_id, filtered_answers, activities_ids, users_and_visits[user]
                )

            logger.info(f"Successfully send data for user: {user}," f" with loris id: {candidate_id}")

        await self._create_integration_alerts(self.applet_id, message=LorisIntegrationAlertMessages.SUCCESS.value)
        logger.info("All finished")

    async def _clear_activities_map(self, activities_map, users_and_visits) -> dict:
        _keys = set()
        for inner_dict in users_and_visits.values():
            _keys.update(["__".join(key.split("__", 2)[:2]) for key in inner_dict.keys()])

        activities_map_filtered = {key: value for key, value in activities_map.items() if key in _keys}
        return activities_map_filtered

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

    async def _ml_answer_to_loris(  # noqa: C901
        self, answer_id: str, activity_id: str, version: str, items: list, data: list
    ) -> dict:
        loris_answers: dict = {}

        for i in range(len(items)):
            if not data[i]:
                continue

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

    async def _get_existing_versions_from_loris(self, headers: dict) -> str:
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
                    await self._create_integration_alerts(
                        self.applet_id, message=LorisIntegrationAlertMessages.LORIS_SERVER_ERROR.value
                    )
                    raise LorisServerError(message=error_message)

    async def _get_existing_answers_from_loris(self, applet_id: str, headers: dict | None = None) -> str:
        if not headers:
            try:
                token: str = await self._login_to_loris()
            except LorisServerError as e:
                logger.info(f"I can't connect to the LORIS server {e}.")
                raise Exception(f"I can't connect to the LORIS server {e}.")

            headers = {
                "Authorization": f"Bearer: {token}",
                "Content-Type": "application/json",
                "accept": "*/*",
            }
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
                    await self._create_integration_alerts(
                        self.applet_id, message=LorisIntegrationAlertMessages.LORIS_SERVER_ERROR.value
                    )
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
                    await self._create_integration_alerts(
                        self.applet_id, message=LorisIntegrationAlertMessages.LORIS_SERVER_ERROR.value
                    )
                    raise LorisServerError(message=error_message)

    async def _create_candidate(
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

                    await self._create_integration_alerts(
                        self.applet_id, message=LorisIntegrationAlertMessages.LORIS_SERVER_ERROR.value
                    )
                    raise LorisServerError(message=error_message)

            async with atomic(relationship_crud.session):
                await relationship_crud.save(
                    MlLorisUserRelationshipSchema(
                        ml_user_uuid=ml_user_id,
                        loris_user_id=candidate_id,
                    )
                )

        return candidate_id

    async def _create_and_start_visits(self, headers: dict, candidate_id: str, visits: list[str]):
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for visit in visits:
                create_visit_url: str = settings.loris.create_visit_url.format(candidate_id, visit)
                logger.info(f"Sending CREATE VISIT request to the loris server {create_visit_url}")
                start = time.time()
                _data_create_visit = {
                    "CandID": candidate_id,
                    "Visit": visit,
                    "Site": "Mindlogger Integration Center",
                    "Battery": "Control",
                    "Project": "loris",
                }
                async with session.put(
                    settings.loris.create_visit_url.format(candidate_id, visit),
                    data=json.dumps(_data_create_visit),
                    headers=headers,
                ) as resp:
                    duration = time.time() - start
                    if resp.status == 201:
                        logger.info(f"Successful request in {duration:.1f} seconds.")
                    elif resp.status == 409:
                        logger.info(f"Failed request in {duration:.1f} seconds.")
                        error_message = await resp.text()
                        logger.info(
                            f"Сannot create visit {visit} for the user {candidate_id} because of: {error_message}"
                        )
                        continue
                    else:
                        logger.info(f"Failed request in {duration:.1f} seconds.")
                        error_message = await resp.text()
                        await self._create_integration_alerts(
                            self.applet_id, message=LorisIntegrationAlertMessages.LORIS_SERVER_ERROR.value
                        )
                        raise LorisServerError(message=error_message)

                start_visit_url: str = settings.loris.start_visit_url.format(candidate_id, visit)
                logger.info(f"Sending START VISIT request to the loris server {start_visit_url}")
                start = time.time()
                _data_start_visit = {
                    "CandID": candidate_id,
                    "Visit": visit,
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
                    settings.loris.start_visit_url.format(candidate_id, visit),
                    data=json.dumps(_data_start_visit),
                    headers=headers,
                ) as resp:
                    duration = time.time() - start
                    if resp.status == 204:
                        logger.info(f"Successful request in {duration:.1f} seconds.")
                    elif resp.status == 409:
                        logger.info(f"Failed request in {duration:.1f} seconds.")
                        error_message = await resp.text()
                        logger.info(
                            f"Сannot start visit {visit} for the user {candidate_id} because of: {error_message}"
                        )
                        continue
                    else:
                        logger.info(f"Failed request in {duration:.1f} seconds.")
                        error_message = await resp.text()
                        raise LorisServerError(message=error_message)

    async def _add_instrument_to_loris(
        self, headers: dict, candidate_id: str, activities_ids: list, user_and_visits: dict
    ):
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for activity_id in activities_ids:
                for key, visit in user_and_visits.items():
                    if key.startswith(activity_id):
                        logger.info(
                            f"Sending ADD INSTRUMENTS request to the loris server "
                            f"{settings.loris.add_instruments_url.format(candidate_id, visit)}"
                        )
                        start = time.time()
                        _data_add_instruments = {
                            "Meta": {
                                "Candidate": candidate_id,
                                "Visit": visit,
                            },
                            "Instruments": [activity_id],
                        }
                        async with session.post(
                            settings.loris.add_instruments_url.format(candidate_id, visit),
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
                                await self._create_integration_alerts(
                                    self.applet_id, message=LorisIntegrationAlertMessages.LORIS_SERVER_ERROR.value
                                )
                                raise LorisServerError(message=error_message)

    async def _add_instrument_data_to_loris(
        self, headers: dict, candidate_id: str, answer: dict, activities_ids: list, user_and_visits: dict
    ):
        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for activity_id in activities_ids:
                answer_by_activity_id = {key: value for key, value in answer.items() if activity_id in key}
                for key, visit in user_and_visits.items():
                    if answer_by_activity_id and key.startswith(activity_id):
                        specific_answers = {k: v for k, v in answer_by_activity_id.items() if k.startswith(key)}
                        if specific_answers:
                            logger.info(
                                f"Sending SEND INSTUMENT DATA request to the loris server "
                                f"{settings.loris.instrument_data_url.format(candidate_id, visit, activity_id)}"
                            )
                            start = time.time()
                            _data_instrument_data = {
                                "Meta": {
                                    "Instrument": activity_id,
                                    "Visit": visit,
                                    "Candidate": candidate_id,
                                    "DDE": True,
                                },
                                activity_id: specific_answers,
                            }
                            logger.info(f"Sending SEND INSTUMENT DATA is : {json.dumps(_data_instrument_data)}")
                            async with session.put(
                                settings.loris.instrument_data_url.format(candidate_id, visit, activity_id),
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
                                    await self._create_integration_alerts(
                                        self.applet_id, message=LorisIntegrationAlertMessages.LORIS_SERVER_ERROR.value
                                    )
                                    raise LorisServerError(message=error_message)

    async def get_visits_list(self) -> list[str]:
        try:
            token: str = await self._login_to_loris()
        except LorisServerError as e:
            logger.info(f"I can't connect to the LORIS server {e}.")

        headers = {
            "Authorization": f"Bearer: {token}",
            "Content-Type": "application/json",
            "accept": "*/*",
        }

        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info(
                f"Sending GET VISITS LIST request to the loris server "
                f"{settings.loris.get_visits_list_url.format('loris')}"
            )
            start = time.time()
            async with session.get(
                settings.loris.get_visits_list_url.format("loris"),
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 200:
                    logger.info(f"Successful request in {duration:.1f} seconds.")
                    visits_data = await resp.json()
                    return visits_data["Visits"]
                else:
                    logger.info(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

    async def get_visits_for_applet(self) -> dict:
        try:
            token: str = await self._login_to_loris()
        except LorisServerError as e:
            logger.info(f"I can't connect to the LORIS server {e}.")

        headers = {
            "Authorization": f"Bearer: {token}",
            "Content-Type": "application/json",
            "accept": "*/*",
        }

        timeout = aiohttp.ClientTimeout(total=60)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            logger.info(
                f"Sending GET VISITS FOR APPLET request to the loris server "
                f"{settings.loris.ml_visits_for_applet_url.format(str(self.applet_id))}"
            )
            start = time.time()
            async with session.get(
                settings.loris.ml_visits_for_applet_url.format(str(self.applet_id)),
                headers=headers,
            ) as resp:
                duration = time.time() - start
                if resp.status == 200:
                    logger.info(f"Successful request in {duration:.1f} seconds.")
                    visits_data = await resp.json()
                    return visits_data
                else:
                    logger.info(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise LorisServerError(message=error_message)

    async def get_uploadable_answers(self) -> tuple[UploadableAnswersData, int]:
        uploaded_answers, applet_visits, answers = await asyncio.gather(
            self._get_existing_answers_from_loris(str(self.applet_id)),
            self.get_visits_for_applet(),
            # todo pagination
            AnswersCRUD(self.answer_session).get_shareable_answers(applet_id=self.applet_id),
        )

        uploaded_answer_ids = set(uploaded_answers)
        del uploaded_answers

        answers_to_upload, respondent_ids, activity_history_ids = [], set(), set()
        for answer in answers:
            if str(answer.id) in uploaded_answer_ids:
                continue
            answers_to_upload.append(answer)
            respondent_ids.add(answer.respondent_id)
            activity_history_ids.add(answer.activity_history_id)

        del answers

        if not answers_to_upload:
            logger.info(
                f"No answers found for given applet: \
                    {str(self.applet_id)}. End of the synchronization."
            )
            return UploadableAnswersData(), 0

        subjects, activity_histories = await asyncio.gather(
            SubjectsCrud(self.session).get_by_user_ids(self.applet_id, list(respondent_ids)),
            ActivityHistoriesCRUD(self.session).get_by_history_ids(list(activity_history_ids)),
        )

        respondent_map = {subj.user_id: subj for subj in subjects}
        relationships = await MlLorisUserRelationshipCRUD(self.session).get_by_ml_user_ids(list(respondent_map.keys()))
        relationships_map: dict[str, list[uuid.UUID]] = defaultdict(list[uuid.UUID])
        for rel in relationships:
            relationships_map[rel.loris_user_id].append(rel.ml_user_uuid)

        activity_history_map = {hist.id_version: hist for hist in activity_histories}
        activity_ids = {str(HistoryAware().id_from_history_id(v)) for v in activity_history_ids}

        # collect affected activity visits formatted as {activity_id: {user_id: {visit1, visit2, ...}}}
        _activity_visits: dict[str, dict[uuid.UUID, UserVisits]] = defaultdict(dict)
        for activity_key, user_visits in (applet_visits or {}).items():
            activity_id = activity_key.split("__")[0]
            if activity_id in activity_ids:
                for user_visit in user_visits:
                    if _user_ids := relationships_map.get(str(user_visit["CandID"])):
                        for _user_id in _user_ids:
                            _visit = _activity_visits[activity_id].get(_user_id) or UserVisits(user_id=_user_id)
                            _visit.visits.update(user_visit["Visits"])
                            _activity_visits[activity_id][_user_id] = _visit
        activity_visits: dict[str, list[UserVisits]] = {k: list(v.values()) for k, v in _activity_visits.items()}

        # collect answers
        answers_data = []
        for _answer in answers_to_upload:
            answers_data.append(
                AnswerData(
                    answer_id=_answer.id,
                    activity_id=HistoryAware().id_from_history_id(_answer.activity_history_id),
                    version=_answer.version,
                    activity_name=activity_history_map[_answer.activity_history_id].name,
                    user_id=_answer.respondent_id,
                    secret_user_id=respondent_map[_answer.respondent_id].secret_user_id,
                    completed_date=_answer.created_at,
                )
            )
        return UploadableAnswersData(activity_visits=activity_visits, answers=answers_data), len(answers_data)

    async def _transform_users_and_visits(self, users_and_visits: list, data: dict) -> dict:
        _data: dict = {}
        for uv in users_and_visits:
            user_id_str = str(uv.user_id)
            if user_id_str in data:
                _activity_data: dict = {}
                for activity in uv.activities:
                    key = f"{activity.activity_id}__{activity.version}__{activity.answer_id}"
                    for data_key in data[user_id_str]:
                        if data_key.startswith(key):
                            _activity_data[key] = activity.visit
                if _activity_data:
                    _data[user_id_str] = _activity_data
        return _data

    async def _create_integration_alerts(self, applet_id: uuid.UUID, message: str):
        latest_versions = await AppletHistoriesCRUD(self.session).get_versions_by_applet_id(self.applet_id)
        version = latest_versions[-1]
        cache = RedisCache()
        user_applet_access = UserAppletAccessCRUD(self.session)
        persons = await user_applet_access.get_responsible_persons(applet_id=applet_id, subject_id=None)
        alert_schemas = []

        for person in persons:
            alert_schemas.append(
                AlertSchema(
                    user_id=person.id,
                    respondent_id=self.user.id,
                    is_watched=False,
                    applet_id=applet_id,
                    alert_message=message,
                    type=AlertTypes.INTEGRATION_ALERT.value,
                    version=version,
                )
            )
        alert_crud = AlertCRUD(self.session)
        async with atomic(alert_crud.session):
            alerts = await alert_crud.create_many(alert_schemas)

        for alert in alerts:
            channel_id = f"channel_{alert.user_id}"

            try:
                await cache.publish(
                    channel_id,
                    AlertMessage(
                        id=alert.id,
                        respondent_id=self.user.id,
                        applet_id=applet_id,
                        version=version,
                        message=alert.alert_message,
                        created_at=alert.created_at,
                        activity_id=alert.activity_id,
                        activity_item_id=alert.activity_item_id,
                        type=alert.type,
                    ).dict(),
                )

            except Exception as e:
                sentry_sdk.capture_exception(e)
                break

    async def create_loris_integration(self, hostname, username, project) -> LorisIntegration:
        integration_schema = await IntegrationsCRUD(self.session).create(
            IntegrationsSchema(
                applet_id=self.applet_id,
                type=self.type,
                configuration={
                    "hostname": hostname,
                    "username": username,
                    "project": project,
                },
            )
        )
        return LorisIntegrationPublic.from_schema(integration_schema)

    async def get_loris_projects(self, hostname, username, password) -> LorisProjects:
        token = await LorisClient.login_to_loris(hostname, username, password)
        projects_raw = await LorisClient.list_projects(hostname, token)
        projects = list(projects_raw["Projects"].keys())
        return LorisProjects(projects=projects)
