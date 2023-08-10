import asyncio
import base64
import datetime
import json
import uuid
from collections import defaultdict

import aiohttp
import sentry_sdk
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from apps.activities.crud import (
    ActivityHistoriesCRUD,
    ActivityItemHistoriesCRUD,
)
from apps.activities.domain.activity_history import ActivityHistoryFull
from apps.activities.services import ActivityHistoryService
from apps.activities.services.activity_item_history import (
    ActivityItemHistoryService,
)
from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.db.schemas import AlertSchema
from apps.alerts.domain import AlertMessage
from apps.answers.crud import AnswerItemsCRUD
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.crud.notes import AnswerNotesCRUD
from apps.answers.db.schemas import (
    AnswerItemSchema,
    AnswerNoteSchema,
    AnswerSchema,
)
from apps.answers.domain import (
    ActivityAnswer,
    AnswerAlert,
    AnswerDate,
    AnswerExport,
    AnswerNoteDetail,
    AnswerReview,
    AppletActivityAnswer,
    AppletAnswerCreate,
    AssessmentAnswer,
    AssessmentAnswerCreate,
    Identifier,
    ReportServerResponse,
    ReviewActivity,
    SummaryActivity,
    Version,
)
from apps.answers.domain.analytics import AnswersMobileData
from apps.answers.errors import (
    ActivityIsNotAssessment,
    AnswerAccessDeniedError,
    AnswerNoteAccessDeniedError,
    NonPublicAppletError,
    ReportServerError,
    ReportServerIsNotConfigured,
    UserDoesNotHavePermissionError,
    WrongAnswerGroupAppletId,
    WrongAnswerGroupVersion,
    WrongRespondentForAnswerGroup,
)
from apps.applets.crud import AppletsCRUD
from apps.applets.domain.base import Encryption
from apps.applets.service import AppletHistoryService
from apps.shared.query_params import QueryParams
from apps.workspaces.crud.applet_access import AppletAccessCRUD
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from infrastructure.utility import RedisCache
from infrastructure.utility.rabbitmq_queue import RabbitMqQueue


class AnswerService:
    def __init__(self, session, user_id: uuid.UUID | None = None):
        self.user_id = user_id
        self.session = session

    @staticmethod
    def _generate_history_id(version: str):
        def key_generator(pk: uuid.UUID):
            return f"{pk}_{version}"

        return key_generator

    async def create_answer(self, activity_answer: AppletAnswerCreate):
        if self.user_id:
            await self._create_respondent_answer(activity_answer)
        else:
            await self._create_anonymous_answer(activity_answer)

    async def _create_respondent_answer(
        self, activity_answer: AppletAnswerCreate
    ):
        await self._validate_respondent_answer(activity_answer)
        await self._create_answer(activity_answer)

    async def _create_anonymous_answer(
        self, activity_answer: AppletAnswerCreate
    ):
        await self._validate_anonymous_answer(activity_answer)
        await self._create_answer(activity_answer)

    async def _validate_respondent_answer(
        self, activity_answer: AppletAnswerCreate
    ):
        await self._validate_answer(activity_answer)
        await self._validate_applet_for_user_response(
            activity_answer.applet_id
        )

    async def _validate_anonymous_answer(
        self, activity_answer: AppletAnswerCreate
    ):
        await self._validate_applet_for_anonymous_response(
            activity_answer.applet_id, activity_answer.version
        )
        await self._validate_answer(activity_answer)

    async def _validate_answer(self, applet_answer: AppletAnswerCreate):
        existed_answers = await AnswersCRUD(self.session).get_by_submit_id(
            applet_answer.submit_id
        )

        if existed_answers:
            existed_answer = existed_answers[0]
            if existed_answer.applet_id != applet_answer.applet_id:
                raise WrongAnswerGroupAppletId()
            elif existed_answer.version != applet_answer.version:
                raise WrongAnswerGroupVersion()
            elif existed_answer.respondent_id != self.user_id:
                raise WrongRespondentForAnswerGroup()

    async def _validate_applet_for_anonymous_response(
        self, applet_id: uuid.UUID, version: str
    ):
        await AppletHistoryService(self.session, applet_id, version).get()
        # Validate applet for anonymous answer
        schema = await AppletsCRUD(self.session).get_by_id(applet_id)
        if not schema.link:
            raise NonPublicAppletError()

    async def _validate_applet_for_user_response(self, applet_id: uuid.UUID):
        assert self.user_id

        roles = await UserAppletAccessService(
            self.session, self.user_id, applet_id
        ).get_roles()
        if not roles:
            raise UserDoesNotHavePermissionError()

    async def _create_answer(self, applet_answer: AppletAnswerCreate):
        pk = self._generate_history_id(applet_answer.version)
        created_at = datetime.datetime.now()
        if applet_answer.created_at:
            created_at = datetime.datetime.fromtimestamp(
                applet_answer.created_at
            )
        answer = await AnswersCRUD(self.session).create(
            AnswerSchema(
                submit_id=applet_answer.submit_id,
                created_at=created_at,
                applet_id=applet_answer.applet_id,
                version=applet_answer.version,
                applet_history_id=pk(applet_answer.applet_id),
                flow_history_id=pk(applet_answer.flow_id)
                if applet_answer.flow_id
                else None,
                activity_history_id=pk(applet_answer.activity_id),
                respondent_id=self.user_id,
                client=applet_answer.client.dict(),
            )
        )
        item_answer = applet_answer.answer

        item_answer = AnswerItemSchema(
            answer_id=answer.id,
            answer=item_answer.answer,
            events=item_answer.events,
            respondent_id=self.user_id,
            user_public_key=item_answer.user_public_key,
            item_ids=item_answer.item_ids,
            identifier=item_answer.identifier,
            scheduled_datetime=datetime.datetime.fromtimestamp(
                item_answer.scheduled_time
            )
            if item_answer.scheduled_time
            else None,
            start_datetime=datetime.datetime.fromtimestamp(
                item_answer.start_time
            ),
            end_datetime=datetime.datetime.fromtimestamp(item_answer.end_time),
            is_assessment=False,
        )

        await AnswerItemsCRUD(self.session).create(item_answer)
        await self._create_report_from_answer(answer.submit_id, answer.id)
        await self._create_alerts(
            answer.id,
            answer.applet_id,
            applet_answer.activity_id,
            answer.version,
            applet_answer.alerts,
        )

    async def _create_report_from_answer(
        self, submit_id: uuid.UUID, answer_id: uuid.UUID
    ):
        service = ReportServerService(self.session)
        is_reportable = await service.is_reportable(answer_id)
        if not is_reportable:
            return

        queue = RabbitMqQueue()
        await queue.connect()
        is_flow_single = await service.is_flows_single_report(answer_id)
        try:
            if not is_flow_single:
                await queue.publish(
                    data=dict(submit_id=submit_id, answer_id=answer_id)
                )
            else:
                # TODO: check whether the flow is finished
                is_single_report = True
                if is_single_report:
                    await queue.publish(data=dict(submit_id=submit_id))
        finally:
            await queue.close()

    async def get_review_activities(
        self,
        applet_id: uuid.UUID,
        respondent_id: uuid.UUID,
        created_date: datetime.date,
    ) -> list[ReviewActivity]:
        await self._validate_applet_activity_access(applet_id, respondent_id)
        answers = await AnswersCRUD(
            self.session
        ).get_respondents_answered_activities_by_applet_id(
            respondent_id, applet_id, created_date
        )
        activity_map: dict[str, ReviewActivity] = dict()
        if not answers:
            applet = await AppletsCRUD(self.session).get_by_id(applet_id)
            activities = await ActivityHistoryService(
                self.session, applet_id, applet.version
            ).activities_list()
            for activity in activities:
                activity_map[str(activity.id)] = ReviewActivity(
                    id=activity.id, name=activity.name
                )
        else:
            answer_map = dict()
            for answer in answers:
                answer_map[answer.id] = answer
                activities = await ActivityHistoryService(
                    self.session, applet_id, answer.version
                ).activities_list()
                for activity in activities:
                    activity_map[str(activity.id)] = ReviewActivity(
                        id=activity.id, name=activity.name
                    )

            answer_items = await AnswerItemsCRUD(self.session).get_answer_ids(
                list(answer_map.keys())
            )

            answer_item_duplicate = set()
            for answer_item in answer_items:
                answer = answer_map[answer_item.answer_id]
                activity_id, version = answer.activity_history_id.split("_")
                key = f"{answer.id}|{activity_id}"
                if key in answer_item_duplicate:
                    continue
                answer_item_duplicate.add(key)
                activity_map[activity_id].answer_dates.append(
                    AnswerDate(
                        created_at=answer_item.created_at, answer_id=answer.id
                    )
                )
        return list(activity_map.values())

    async def get_applet_submit_dates(
        self,
        applet_id: uuid.UUID,
        respondent_id: uuid.UUID,
        from_date: datetime.date,
        to_date: datetime.date,
    ) -> list[datetime.date]:
        await self._validate_applet_activity_access(applet_id, respondent_id)
        return await AnswersCRUD(self.session).get_respondents_submit_dates(
            respondent_id, applet_id, from_date, to_date
        )

    async def _validate_applet_activity_access(
        self, applet_id: uuid.UUID, respondent_id: uuid.UUID
    ):
        assert self.user_id, "User id is required"
        await AppletsCRUD(self.session).get_by_id(applet_id)
        role = await AppletAccessCRUD(self.session).get_applets_priority_role(
            applet_id, self.user_id
        )
        if role == Role.REVIEWER:
            access = await UserAppletAccessService(
                self.session, self.user_id, applet_id
            ).get_access(Role.REVIEWER)
            assert access is not None

            if str(respondent_id) not in access.meta.get("respondents", []):
                raise AnswerAccessDeniedError()

    async def get_by_id(
        self,
        applet_id: uuid.UUID,
        answer_id: uuid.UUID,
        activity_id: uuid.UUID,
    ) -> ActivityAnswer:
        await self._validate_answer_access(applet_id, answer_id, activity_id)

        schema = await AnswersCRUD(self.session).get_by_id(answer_id)
        pk = self._generate_history_id(schema.version)
        answer_items = await AnswerItemsCRUD(
            self.session
        ).get_by_answer_and_activity(answer_id, pk(activity_id))
        answer_item = answer_items[0]

        activity_items = await ActivityItemHistoryService(
            self.session, applet_id, schema.version
        ).get_by_activity_id(activity_id)

        answer = ActivityAnswer(
            user_public_key=answer_item.user_public_key,
            answer=answer_item.answer,
            item_ids=answer_item.item_ids,
            items=activity_items,
            events=answer_item.events,
        )

        return answer

    async def _validate_answer_access(
        self,
        applet_id: uuid.UUID,
        answer_id: uuid.UUID,
        activity_id: uuid.UUID | None = None,
    ):
        answer_schema = await AnswersCRUD(self.session).get_by_id(answer_id)
        await self._validate_applet_activity_access(
            applet_id, answer_schema.respondent_id
        )
        if activity_id:
            pk = self._generate_history_id(answer_schema.version)
            await ActivityHistoriesCRUD(self.session).get_by_id(
                pk(activity_id)
            )

    async def add_note(
        self,
        applet_id: uuid.UUID,
        answer_id: uuid.UUID,
        activity_id: uuid.UUID,
        note: str,
    ):
        await self._validate_answer_access(applet_id, answer_id, activity_id)
        schema = AnswerNoteSchema(
            answer_id=answer_id,
            note=note,
            user_id=self.user_id,
            activity_id=activity_id,
        )
        await AnswerNotesCRUD(self.session).save(schema)

    async def get_note_list(
        self,
        applet_id: uuid.UUID,
        answer_id: uuid.UUID,
        activity_id: uuid.UUID,
        query_params: QueryParams,
    ) -> list[AnswerNoteDetail]:
        await self._validate_answer_access(applet_id, answer_id, activity_id)
        notes = await AnswerNotesCRUD(self.session).get_by_answer_id(
            answer_id, activity_id, query_params
        )
        return notes

    async def get_notes_count(
        self,
        answer_id: uuid.UUID,
        activity_id: uuid.UUID,
    ) -> int:
        return await AnswerNotesCRUD(self.session).get_count_by_answer_id(
            answer_id, activity_id
        )

    async def edit_note(
        self,
        applet_id: uuid.UUID,
        answer_id: uuid.UUID,
        activity_id: uuid.UUID,
        note_id: uuid.UUID,
        note: str,
    ):
        await self._validate_answer_access(applet_id, answer_id, activity_id)
        await self._validate_note_access(note_id)
        await AnswerNotesCRUD(self.session).update_note_by_id(note_id, note)

    async def delete_note(
        self,
        applet_id: uuid.UUID,
        answer_id: uuid.UUID,
        activity_id: uuid.UUID,
        note_id: uuid.UUID,
    ):
        await self._validate_answer_access(applet_id, answer_id, activity_id)
        await self._validate_note_access(note_id)
        await AnswerNotesCRUD(self.session).delete_note_by_id(note_id)

    async def _validate_note_access(self, note_id: uuid.UUID):
        note = await AnswerNotesCRUD(self.session).get_by_id(note_id)
        if note.user_id != self.user_id:
            raise AnswerNoteAccessDeniedError()

    async def get_assessment_by_answer_id(
        self, applet_id: uuid.UUID, answer_id: uuid.UUID
    ) -> AssessmentAnswer:
        assert self.user_id

        await self._validate_answer_access(applet_id, answer_id)
        schema = await AnswersCRUD(self.session).get_by_id(answer_id)
        pk = self._generate_history_id(schema.version)

        activity_items = await ActivityItemHistoriesCRUD(
            self.session
        ).get_applets_assessments(pk(applet_id))
        if len(activity_items) == 0:
            return AssessmentAnswer(items=activity_items)

        assessment_answer = await AnswerItemsCRUD(self.session).get_assessment(
            answer_id, self.user_id
        )

        answer = AssessmentAnswer(
            reviewer_public_key=assessment_answer.user_public_key
            if assessment_answer
            else None,
            answer=assessment_answer.answer if assessment_answer else None,
            item_ids=assessment_answer.item_ids if assessment_answer else [],
            items=activity_items,
            is_edited=assessment_answer.created_at
            != assessment_answer.updated_at  # noqa
            if assessment_answer
            else False,
        )
        return answer

    async def get_reviews_by_answer_id(
        self, applet_id: uuid.UUID, answer_id: uuid.UUID
    ) -> list[AnswerReview]:
        assert self.user_id

        await self._validate_answer_access(applet_id, answer_id)
        schema = await AnswersCRUD(self.session).get_by_id(answer_id)
        pk = self._generate_history_id(schema.version)

        activity_items = await ActivityItemHistoriesCRUD(
            self.session
        ).get_applets_assessments(pk(applet_id))

        reviews = await AnswerItemsCRUD(self.session).get_reviews_by_answer_id(
            answer_id, activity_items
        )
        return reviews

    async def create_assessment_answer(
        self,
        applet_id: uuid.UUID,
        answer_id: uuid.UUID,
        schema: AssessmentAnswerCreate,
    ):
        assert self.user_id

        await self._validate_answer_access(applet_id, answer_id)
        assessment = await AnswerItemsCRUD(self.session).get_assessment(
            answer_id, self.user_id
        )
        if assessment:
            await AnswerItemsCRUD(self.session).update(
                AnswerItemSchema(
                    id=assessment.id,
                    created_at=assessment.created_at,
                    updated_at=datetime.datetime.now(),
                    answer_id=answer_id,
                    respondent_id=self.user_id,
                    answer=schema.answer,
                    item_ids=list(map(str, schema.item_ids)),
                    user_public_key=schema.reviewer_public_key,
                    is_assessment=True,
                    start_datetime=datetime.datetime.now(),
                    end_datetime=datetime.datetime.now(),
                )
            )
        else:
            now = datetime.datetime.now()
            await AnswerItemsCRUD(self.session).create(
                AnswerItemSchema(
                    answer_id=answer_id,
                    respondent_id=self.user_id,
                    answer=schema.answer,
                    item_ids=list(map(str, schema.item_ids)),
                    user_public_key=schema.reviewer_public_key,
                    is_assessment=True,
                    start_datetime=now,
                    end_datetime=now,
                    created_at=now,
                    updated_at=now,
                )
            )

    async def _validate_activity_for_assessment(
        self, activity_history_id: str
    ):
        schema = await ActivityHistoriesCRUD(self.session).get_by_id(
            activity_history_id
        )

        if not schema.is_reviewable:
            raise ActivityIsNotAssessment()

    async def get_export_data(
        self, applet_id: uuid.UUID, query_params: QueryParams
    ) -> AnswerExport:
        assert self.user_id is not None

        repository = AnswersCRUD(self.session)
        answers = await repository.get_applet_answers(
            applet_id, self.user_id, **query_params.filters
        )

        if not answers:
            return AnswerExport()

        activity_hist_ids = list(
            {answer.activity_history_id for answer in answers}
        )

        activities, items = await asyncio.gather(
            repository.get_activity_history_by_ids(activity_hist_ids),
            repository.get_item_history_by_activity_history(activity_hist_ids),
        )

        activity_map = {
            activity.id_version: ActivityHistoryFull.from_orm(activity)
            for activity in activities
        }
        for item in items:
            activity = activity_map.get(item.activity_id)
            if activity:
                activity.items.append(item)

        return AnswerExport(
            answers=answers, activities=list(activity_map.values())
        )

    async def get_activity_identifiers(
        self,
        activity_id: uuid.UUID,
    ) -> list[Identifier]:
        await ActivityHistoriesCRUD(
            self.session
        ).exist_by_activity_id_or_raise(activity_id)
        identifiers = await AnswersCRUD(
            self.session
        ).get_identifiers_by_activity_id(activity_id)
        results = []
        for identifier, key in identifiers:
            results.append(
                Identifier(
                    identifier=identifier,
                    user_public_key=key,
                )
            )
        return results

    async def get_activity_versions(
        self,
        activity_id: uuid.UUID,
    ) -> list[Version]:
        await ActivityHistoriesCRUD(
            self.session
        ).exist_by_activity_id_or_raise(activity_id)
        return await AnswersCRUD(self.session).get_versions_by_activity_id(
            activity_id
        )

    async def get_activity_answers(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID,
        filters: QueryParams,
    ) -> list[AppletActivityAnswer]:
        versions = filters.filters.get("versions")

        if versions and isinstance(versions, str):
            versions = versions.split(",")

        activities = await ActivityHistoriesCRUD(self.session).get_activities(
            activity_id, versions
        )

        activity_items = await ActivityItemHistoriesCRUD(
            self.session
        ).get_activity_items(activity_id, versions)
        answers = await AnswerItemsCRUD(
            self.session
        ).get_applet_answers_by_activity_id(applet_id, activity_id, filters)

        activity_item_map = defaultdict(list)
        for activity_item in activity_items:
            activity_item_map[activity_item.activity_id].append(activity_item)

        activity_map = dict()
        for activity in activities:
            activity_map[activity.id_version] = activity

        activity_answers = list()
        for answer, answer_item in answers:
            if not answer_item:
                continue
            answer_item.items = activity_item_map.get(
                answer.activity_history_id, []
            )
            activity_answer = AppletActivityAnswer.from_orm(answer_item)
            if answer_item.items:
                activity = activity_map[answer_item.items[0].activity_id]
                activity_answer.subscale_setting = activity.subscale_setting
            activity_answer.version = answer.version
            activity_answers.append(activity_answer)
        return activity_answers

    async def get_summary_latest_report(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID,
        respondent_id: uuid.UUID,
    ) -> ReportServerResponse | None:
        answer = await AnswersCRUD(self.session).get_latest_answer(
            applet_id, activity_id, respondent_id
        )
        if not answer:
            return None
        service = ReportServerService(self.session)
        await self._is_report_server_configured(applet_id)
        is_single_flow = await service.is_flows_single_report(answer.id)
        if is_single_flow:
            report = await service.create_report(answer.submit_id)
        else:
            report = await service.create_report(answer.submit_id, answer.id)

        return report

    async def _is_report_server_configured(self, applet_id: uuid.UUID):
        applet = await AppletsCRUD(self.session).get_by_id(applet_id)
        if not applet.report_server_ip:
            raise ReportServerIsNotConfigured()
        if not applet.report_public_key:
            raise ReportServerIsNotConfigured()

    async def get_summary_activities(
        self, applet_id: uuid.UUID, respondent_id: uuid.UUID | None
    ) -> list[SummaryActivity]:
        activities = await ActivityHistoriesCRUD(
            self.session
        ).get_by_applet_id_for_summary(applet_id)
        activity_ids = [activity.id for activity in activities]
        activity_ids_with_answer = await AnswersCRUD(
            self.session
        ).get_activities_which_has_answer(activity_ids, respondent_id)
        results = []
        for activity in activities:
            results.append(
                SummaryActivity(
                    id=activity.id,
                    name=activity.name,
                    is_performance_task=activity.is_performance_task,
                    has_answer=activity.id in activity_ids_with_answer,
                )
            )
        return results

    async def _create_alerts(
        self,
        answer_id: uuid.UUID,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID,
        version: str,
        raw_alerts: list[AnswerAlert],
    ):
        if len(raw_alerts) == 0:
            return
        cache = RedisCache()
        receiver_ids = await UserAppletAccessCRUD(
            self.session
        ).get_responsible_persons(applet_id, self.user_id)
        alert_schemas = []
        for receiver_id in receiver_ids:
            for raw_alert in raw_alerts:
                alert_schemas.append(
                    AlertSchema(
                        user_id=receiver_id,
                        respondent_id=self.user_id,
                        is_watched=False,
                        applet_id=applet_id,
                        version=version,
                        activity_id=activity_id,
                        activity_item_id=raw_alert.activity_item_id,
                        alert_message=raw_alert.message,
                        answer_id=answer_id,
                    )
                )

        alerts = await AlertCRUD(self.session).create_many(alert_schemas)

        for alert in alerts:
            channel_id = f"channel_{alert.user_id}"
            try:
                await cache.publish(
                    channel_id,
                    AlertMessage(
                        id=alert.id,
                        respondent_id=self.user_id,
                        applet_id=applet_id,
                        version=version,
                        message=alert.alert_message,
                        created_at=alert.created_at,
                        activity_id=alert.activity_id,
                        activity_item_id=alert.activity_item_id,
                        answer_id=answer_id,
                    ).dict(),
                )
            except Exception as e:
                sentry_sdk.capture_exception(e)
                break

    async def get_answer_mobile_data(self, applet_id: uuid.UUID):
        answers = await AnswersCRUD(
            self.session
        ).get_answers_by_applet_respondent(self.user_id, applet_id)

        answer_item_id_list = []

        response = {}
        response_config = {}
        activities_responses = []
        activity_response = {}
        applet_analytics = {}
        data = []

        for answer in answers:
            applet_analytics["applet_id"] = applet_id
            answer_item = await AnswerItemsCRUD(
                self.session
            ).get_respondent_answer(answer.id)
            answer_item_ids = answer_item.item_ids
            for answer_item_id in answer_item_ids:
                if answer_item_id not in answer_item_id_list:
                    activity_item_history = await ActivityItemHistoriesCRUD(
                        self.session
                    ).retrieve_by_id(answer_item_id)

                    activity_history = await ActivityHistoriesCRUD(
                        self.session
                    ).get_by_id(activity_item_history.activity_id)

                    activity_id = activity_history.id
                    activity_name = activity_history.name

                    if activity_item_history.response_type in [
                        "singleSelect",
                        "multiSelect",
                        "slider",
                    ]:
                        response["type"] = activity_item_history.response_type
                        response["name"] = activity_item_history.name

                        options_full_list = (
                            activity_item_history.response_values["options"]
                        )
                        options = []
                        for option in options_full_list:
                            option_new = {
                                "name": option["text"],
                                "value": option["value"],
                            }
                            options.append(option_new)

                            if answer_item.answer == option["id"]:
                                data.append(
                                    {
                                        "date": activity_item_history.created_at,  # noqa
                                        "value": option["value"],
                                    }
                                )

                        response_config["options"] = options
                        activity_response["id"] = activity_id
                        activity_response["name"] = activity_name

                        response["response_config"] = response_config
                        response["data"] = data

                        activity_response["responses"] = [response]

                        activities_responses.append(activity_response)
                        applet_analytics[
                            "activities_responses"
                        ] = activities_responses

                        answer_item_id_list.append(answer_item_id)
                else:
                    activity_item_history = await ActivityItemHistoriesCRUD(
                        self.session
                    ).retrieve_by_id(answer_item_id)
                    if activity_item_history.response_type in [
                        "singleSelect",
                        "multiSelect",
                        "slider",
                    ]:
                        options_full_list = (
                            activity_item_history.response_values["options"]
                        )
                        for option in options_full_list:
                            if answer_item.answer == option["id"]:
                                data.append(
                                    {
                                        "date": activity_item_history.created_at,  # noqa
                                        "value": option["value"],
                                    }
                                )
                        response["data"] = data
                        activity_response["responses"] = [response]
                        applet_analytics[
                            "activities_responses"
                        ] = activities_responses

        return AnswersMobileData(**applet_analytics)


class ReportServerService:
    def __init__(self, session):
        self.session = session

    async def is_reportable(self, answer_id: uuid.UUID):
        answer, applet, activity = await AnswersCRUD(
            self.session
        ).get_applet_info_by_answer_id(answer_id)
        if not applet.report_server_ip:
            return False
        elif not applet.report_public_key:
            return False
        elif not applet.report_recipients:
            return False
        elif not activity.scores_and_reports:
            return False
        elif not activity.scores_and_reports.get("generate_report", False):
            return False

        scores = activity.scores_and_reports.get("scores", [])
        sections = activity.scores_and_reports.get("sections", [])
        if not any([scores, sections]):
            return False
        return True

    async def is_flows_single_report(self, answer_id: uuid.UUID) -> bool:
        """
        Whether check to send flow reports in a single or multiple request
        """
        result = await AnswersCRUD(
            self.session
        ).get_activity_flow_by_answer_id(answer_id)
        return result

    async def create_report(
        self, submit_id: uuid.UUID, answer_id: uuid.UUID | None = None
    ) -> ReportServerResponse | None:
        answers = await AnswersCRUD(self.session).get_by_submit_id(
            submit_id, answer_id
        )
        if not answers:
            return None
        answer_map = dict((answer.id, answer) for answer in answers)
        initial_answer = answers[0]

        applet = await AppletsCRUD(self.session).get_by_id(
            initial_answer.applet_id
        )
        user_info = await self._get_user_info(
            initial_answer.respondent_id, initial_answer.applet_id
        )
        applet_full = await self._prepare_applet_data(
            initial_answer.applet_id, initial_answer.version, applet.encryption
        )

        encryption = ReportServerEncryption(applet.report_public_key)
        responses, user_public_keys = await self._prepare_responses(answer_map)

        data = dict(
            responses=responses,
            userPublicKeys=user_public_keys,
            userPublicKey=user_public_keys[0],
            now=datetime.date.today().strftime("%x"),
            user=user_info,
            applet=applet_full,
        )
        encrypted_data = encryption.encrypt(data)

        activity_id, version = initial_answer.activity_history_id.split("_")
        flow_id, version = "", ""
        if initial_answer.flow_history_id:
            flow_id, version = initial_answer.flow_history_id.split("_")

        url = "{}/send-pdf-report?activityId={}&activityFlowId={}".format(
            applet.report_server_ip, activity_id, flow_id
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json=dict(payload=encrypted_data),
            ) as resp:
                response_data = await resp.json()
                if resp.status == 200:
                    return ReportServerResponse(**response_data)
                else:
                    raise ReportServerError(message=str(response_data))

    async def _prepare_applet_data(
        self, applet_id: uuid.UUID, version: str, encryption: dict
    ):
        applet_full = await AppletHistoryService(
            self.session, applet_id, version
        ).get_full()
        applet_full.encryption = Encryption(**encryption)
        return applet_full.dict(by_alias=True)

    async def _get_user_info(
        self, respondent_id: uuid.UUID, applet_id: uuid.UUID
    ):
        access = await UserAppletAccessCRUD(self.session).get(
            respondent_id, applet_id, Role.RESPONDENT
        )
        assert access
        return dict(
            firstName=access.meta.get("firstName"),
            lastName=access.meta.get("lastName"),
            nickname=access.meta.get("nickname"),
            secretId=access.meta.get("secretUserId"),
        )

    async def _prepare_responses(
        self, answers_map: dict[uuid.UUID, AnswerSchema]
    ) -> tuple[list[dict], list[str]]:
        answer_items = await AnswerItemsCRUD(
            self.session
        ).get_respondent_submits_by_answer_ids(list(answers_map.keys()))

        responses = list()
        for answer_item in answer_items:
            answer = answers_map[answer_item.answer_id]
            activity_id, version = answer.activity_history_id.split("_")
            responses.append(
                dict(activityId=activity_id, answer=answer_item.answer)
            )
        return responses, [ai.user_public_key for ai in answer_items]


class ReportServerEncryption:
    _rate = 0.58

    def __init__(self, key: str):
        self.encryption = load_pem_public_key(
            key.encode(), backend=default_backend()
        )

    def encrypt(self, data: dict):
        str_data = json.dumps(data, default=str)
        key_size = getattr(self.encryption, "key_size", 0)
        encrypt = getattr(self.encryption, "encrypt", lambda x, y: x)
        chunk_size = int(key_size / 8 * self._rate)
        chunks = []
        for i in range(len(str_data) // chunk_size + 1):
            beg = i * chunk_size
            end = beg + chunk_size
            encrypted_chunk = encrypt(
                str_data[beg:end].encode(),
                self._get_padding(),
            )
            chunks.append(base64.b64encode(encrypted_chunk).decode())

        return chunks

    def _get_padding(self):
        return padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA1()),
            algorithm=hashes.SHA1(),
            label=None,
        )
