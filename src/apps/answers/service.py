import asyncio
import base64
import datetime
import json
import os
import time
import uuid
from collections import defaultdict
from json import JSONDecodeError
from typing import Callable, List

import aiohttp
import pydantic
import sentry_sdk
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from apps.activities.crud import ActivitiesCRUD, ActivityHistoriesCRUD, ActivityItemHistoriesCRUD
from apps.activities.domain.activity_history import ActivityHistoryFull
from apps.activities.errors import ActivityDoeNotExist, ActivityHistoryDoeNotExist
from apps.activity_flows.crud import FlowsCRUD, FlowsHistoryCRUD
from apps.alerts.crud.alert import AlertCRUD
from apps.alerts.db.schemas import AlertSchema
from apps.alerts.domain import AlertMessage
from apps.answers.crud import AnswerItemsCRUD
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.crud.notes import AnswerNotesCRUD
from apps.answers.db.schemas import AnswerItemSchema, AnswerNoteSchema, AnswerSchema
from apps.answers.domain import (
    ActivityAnswer,
    ActivitySubmission,
    AnswerAlert,
    AnswerDate,
    AnswerExport,
    AnswerItemDataEncrypted,
    AnswerNoteDetail,
    AnswerReview,
    AppletActivityAnswer,
    AppletAnswerCreate,
    AppletCompletedEntities,
    AssessmentAnswer,
    AssessmentAnswerCreate,
    AssessmentItem,
    FlowSubmission,
    FlowSubmissionDetails,
    FlowSubmissionsDetails,
    Identifier,
    ReportServerResponse,
    ReviewActivity,
    ReviewFlow,
    ReviewsCount,
    SubmissionDate,
    SummaryActivity,
    SummaryActivityFlow,
)
from apps.answers.errors import (
    ActivityIsNotAssessment,
    AnswerAccessDeniedError,
    AnswerNoteAccessDeniedError,
    AnswerNotFoundError,
    NonPublicAppletError,
    ReportServerError,
    ReportServerIsNotConfigured,
    UserDoesNotHavePermissionError,
    WrongAnswerGroupAppletId,
    WrongAnswerGroupVersion,
    WrongRespondentForAnswerGroup,
)
from apps.answers.tasks import create_report
from apps.applets.crud import AppletsCRUD
from apps.applets.domain.applet_history import Version
from apps.applets.domain.base import Encryption
from apps.applets.service import AppletHistoryService
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.shared.encryption import decrypt_cbc, encrypt_cbc
from apps.shared.exception import EncryptionError
from apps.shared.query_params import QueryParams
from apps.users import User, UserSchema, UsersCRUD
from apps.users.errors import UserNotFound
from apps.workspaces.crud.applet_access import AppletAccessCRUD
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.domain.workspace import WorkspaceRespondent
from apps.workspaces.service.user_applet_access import UserAppletAccessService
from infrastructure.database.mixins import HistoryAware
from infrastructure.logger import logger
from infrastructure.utility import RedisCache


class AnswerService:
    def __init__(self, session, user_id: uuid.UUID | None = None, arbitrary_session=None):
        self.user_id = user_id
        self.session = session
        self._answer_session = arbitrary_session

    @property
    def answer_session(self):
        return self._answer_session if self._answer_session else self.session

    @staticmethod
    def _generate_history_id(version: str) -> Callable[..., str]:
        def key_generator(pk: uuid.UUID) -> str:
            return HistoryAware.generate_id_version(pk, version)

        return key_generator

    async def create_answer(self, activity_answer: AppletAnswerCreate) -> AnswerSchema:
        if self.user_id:
            return await self._create_respondent_answer(activity_answer)
        else:
            return await self._create_anonymous_answer(activity_answer)

    async def _create_respondent_answer(self, activity_answer: AppletAnswerCreate) -> AnswerSchema:
        await self._validate_respondent_answer(activity_answer)
        return await self._create_answer(activity_answer)

    async def _create_anonymous_answer(self, activity_answer: AppletAnswerCreate) -> AnswerSchema:
        await self._validate_anonymous_answer(activity_answer)
        return await self._create_answer(activity_answer)

    async def _validate_respondent_answer(self, activity_answer: AppletAnswerCreate) -> None:
        await self._validate_answer(activity_answer)
        await self._validate_applet_for_user_response(activity_answer.applet_id)

    async def _validate_anonymous_answer(self, activity_answer: AppletAnswerCreate) -> None:
        await self._validate_applet_for_anonymous_response(activity_answer.applet_id, activity_answer.version)
        await self._validate_answer(activity_answer)

    async def _validate_answer(self, applet_answer: AppletAnswerCreate) -> None:
        existed_answers = await AnswersCRUD(self.session).get_by_submit_id(applet_answer.submit_id)

        if existed_answers:
            existed_answer = existed_answers[0]
            if existed_answer.applet_id != applet_answer.applet_id:
                raise WrongAnswerGroupAppletId()
            elif existed_answer.version != applet_answer.version:
                raise WrongAnswerGroupVersion()
            elif existed_answer.respondent_id != self.user_id:
                raise WrongRespondentForAnswerGroup()

        pk = self._generate_history_id(applet_answer.version)
        activity_history = await ActivityHistoriesCRUD(self.session).get_by_id(pk(applet_answer.activity_id))

        if not activity_history.applet_id.startswith(f"{applet_answer.applet_id}"):
            raise ActivityHistoryDoeNotExist()

    async def _validate_applet_for_anonymous_response(self, applet_id: uuid.UUID, version: str) -> None:
        await AppletHistoryService(self.session, applet_id, version).get()
        # Validate applet for anonymous answer
        schema = await AppletsCRUD(self.session).get_by_id(applet_id)
        if not schema.link:
            raise NonPublicAppletError()

    async def _validate_applet_for_user_response(self, applet_id: uuid.UUID) -> None:
        assert self.user_id

        roles = await UserAppletAccessService(self.session, self.user_id, applet_id).get_roles()
        if not roles:
            raise UserDoesNotHavePermissionError()

    async def _create_answer(self, applet_answer: AppletAnswerCreate) -> AnswerSchema:
        pk = self._generate_history_id(applet_answer.version)
        created_at = applet_answer.created_at or datetime.datetime.utcnow()
        answer = await AnswersCRUD(self.answer_session).create(
            AnswerSchema(
                submit_id=applet_answer.submit_id,
                created_at=created_at,
                applet_id=applet_answer.applet_id,
                version=applet_answer.version,
                applet_history_id=pk(applet_answer.applet_id),
                flow_history_id=pk(applet_answer.flow_id) if applet_answer.flow_id else None,
                activity_history_id=pk(applet_answer.activity_id),
                respondent_id=self.user_id,
                client=applet_answer.client.dict(),
                is_flow_completed=bool(applet_answer.is_flow_completed) if applet_answer.flow_id else None,
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
            scheduled_datetime=item_answer.scheduled_time,
            start_datetime=item_answer.start_time,
            end_datetime=item_answer.end_time,
            is_assessment=False,
            scheduled_event_id=item_answer.scheduled_event_id,
            local_end_date=item_answer.local_end_date,
            local_end_time=item_answer.local_end_time,
            tz_offset=item_answer.tz_offset,
        )

        await AnswerItemsCRUD(self.answer_session).create(item_answer)
        await self._create_alerts(
            answer.id,
            answer.applet_id,
            applet_answer.activity_id,
            answer.version,
            applet_answer.alerts,
        )
        return answer

    async def create_report_from_answer(self, answer: AnswerSchema):
        service = ReportServerService(session=self.session, arbitrary_session=self.answer_session)
        # First check is flow single report or not, flow single report has
        # another rules to be reportable.
        is_flow_single = await service.is_flows_single_report(answer.id)
        if is_flow_single:
            is_flow_finished = await service.is_flow_finished(answer.submit_id, answer.id)
            if is_flow_finished:
                is_reportable = await service.is_reportable(answer, is_flow_single)
                if is_reportable:
                    await create_report.kiq(answer.applet_id, answer.submit_id)
        else:
            is_reportable = await service.is_reportable(answer)
            if is_reportable:
                await create_report.kiq(
                    answer.applet_id,
                    answer.submit_id,
                    answer.id,
                )

    async def get_review_activities(
        self,
        applet_id: uuid.UUID,
        respondent_id: uuid.UUID,
        created_date: datetime.date,
    ) -> list[ReviewActivity]:
        await self._validate_applet_activity_access(applet_id, respondent_id)

        answers_coro = AnswersCRUD(self.answer_session).get_list(
            applet_id=applet_id, respondent_ids=[respondent_id], created_date=created_date
        )
        activities_coro = ActivitiesCRUD(self.session).get_by_applet_id(applet_id, is_reviewable=False)
        answers, activities = await asyncio.gather(answers_coro, activities_coro)

        activity_map: dict[uuid.UUID, ReviewActivity] = dict()
        for activity in activities:
            activity_map[activity.id] = ReviewActivity(id=activity.id, name=activity.name)

        if answers:
            old_activity_answer_dates: dict[uuid.UUID, list[AnswerDate]] = defaultdict(list)
            activity_history_ids = set()
            for answer in answers:
                activity_id, _ = HistoryAware.split_id_version(answer.activity_history_id)
                if _activity := activity_map.get(activity_id):
                    _activity.answer_dates.append(
                        AnswerDate(
                            answer_id=answer.id,
                            created_at=answer.answer_item.created_at,
                            end_datetime=answer.answer_item.end_datetime,
                        )
                    )
                else:
                    old_activity_answer_dates[activity_id].append(
                        AnswerDate(
                            answer_id=answer.id,
                            created_at=answer.answer_item.created_at,
                            end_datetime=answer.answer_item.end_datetime,
                        )
                    )
                    activity_history_ids.add(answer.activity_history_id)

            if activity_history_ids:
                activity_histories = await ActivityHistoriesCRUD(self.session).get_by_history_ids(
                    list(activity_history_ids)
                )
                for activity_history in activity_histories:
                    if activity_history.id not in activity_map:
                        activity_map[activity_history.id] = ReviewActivity(
                            id=activity_history.id,
                            name=activity_history.name,
                            answer_dates=old_activity_answer_dates[activity_history.id],
                        )

        return list(activity_map.values())

    async def get_review_flows(
        self,
        applet_id: uuid.UUID,
        respondent_id: uuid.UUID,
        created_date: datetime.date,
    ) -> list[ReviewFlow]:
        await self._validate_applet_activity_access(applet_id, respondent_id)

        submissions_coro = AnswersCRUD(self.answer_session).get_flow_submission_data(
            applet_id=applet_id, respondent_ids=[respondent_id], created_date=created_date
        )
        flows_coro = FlowsCRUD(self.session).get_by_applet_id(applet_id)
        submissions, flows = await asyncio.gather(submissions_coro, flows_coro)

        flow_map: dict[uuid.UUID, ReviewFlow] = dict()
        for flow in flows:
            flow_map[flow.id] = ReviewFlow(id=flow.id, name=flow.name)

        if submissions:
            old_flow_submission_dates: dict[uuid.UUID, list[SubmissionDate]] = defaultdict(list)
            flow_history_ids = set()
            for submission in submissions:
                flow_id, _ = HistoryAware.split_id_version(submission.flow_history_id)
                _submission_date = SubmissionDate.from_orm(submission)
                if _flow := flow_map.get(flow_id):
                    _flow.answer_dates.append(_submission_date)  # type: ignore[arg-type]
                else:
                    old_flow_submission_dates[flow_id].append(_submission_date)
                    flow_history_ids.add(submission.flow_history_id)

            if flow_history_ids:
                flow_histories = await FlowsHistoryCRUD(self.session).get_by_id_versions(list(flow_history_ids))
                for flow_history in flow_histories:
                    if flow_history.id not in flow_map:
                        flow_map[flow_history.id] = ReviewFlow(
                            id=flow_history.id,
                            name=flow_history.name,
                            answer_dates=old_flow_submission_dates[flow_history.id],
                        )

        return list(flow_map.values())

    async def get_applet_submit_dates(
        self,
        applet_id: uuid.UUID,
        respondent_id: uuid.UUID,
        from_date: datetime.date,
        to_date: datetime.date,
    ) -> list[datetime.date]:
        await self._validate_applet_activity_access(applet_id, respondent_id)
        return await AnswersCRUD(self.answer_session).get_respondents_submit_dates(
            respondent_id, applet_id, from_date, to_date
        )

    async def _validate_applet_activity_access(self, applet_id: uuid.UUID, respondent_id: uuid.UUID):
        assert self.user_id, "User id is required"
        await AppletsCRUD(self.session).get_by_id(applet_id)
        role = await AppletAccessCRUD(self.session).get_applets_priority_role(applet_id, self.user_id)
        if role == Role.REVIEWER:
            access = await UserAppletAccessService(self.session, self.user_id, applet_id).get_access(Role.REVIEWER)
            assert access is not None

            if str(respondent_id) not in access.meta.get("respondents", []):
                raise AnswerAccessDeniedError()

    async def _get_allowed_respondents(self, applet_id: uuid.UUID) -> list[uuid.UUID] | None:
        assert self.user_id
        access = await UserAppletAccessCRUD(self.session).get_by_roles(
            self.user_id,
            applet_id,
            [Role.OWNER, Role.MANAGER, Role.REVIEWER],
        )
        allowed_respondents = None
        if not access:
            allowed_respondents = [self.user_id]
        elif access.role == Role.REVIEWER:
            if isinstance(access.reviewer_respondents, list) and len(access.reviewer_respondents) > 0:
                allowed_respondents = access.reviewer_respondents  # noqa: E501
            else:
                allowed_respondents = [self.user_id]

        return allowed_respondents

    async def get_activity_answer(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID,
        answer_id: uuid.UUID,
    ) -> ActivitySubmission:
        # TODO properly merge to multiinformant using subject ids
        allowed_respondents = await self._get_allowed_respondents(applet_id)

        repository = AnswersCRUD(self.answer_session)
        answers = await repository.get_list(
            applet_id=applet_id,
            activity_id=activity_id,
            answer_id=answer_id,
            respondent_ids=allowed_respondents,
        )
        if not answers:
            raise AnswerNotFoundError()

        answer = answers[0]
        answer_result = ActivityAnswer(
            **answer.dict(exclude={"migrated_data"}),
            **answer.answer_item.dict(
                include={
                    "user_public_key",
                    "answer",
                    "events",
                    "item_ids",
                    "identifier",
                    "migrated_data",
                    "end_datetime",
                }
            ),
        )

        activities = await ActivityHistoriesCRUD(self.session).load_full([answer.activity_history_id])
        assert activities

        submission = ActivitySubmission(
            activity=activities[0],
            answer=answer_result,
        )

        return submission

    async def _validate_answer_access(
        self,
        applet_id: uuid.UUID,
        answer_id: uuid.UUID,
        activity_id: uuid.UUID | None = None,
    ):
        answer_schema = await AnswersCRUD(self.answer_session).get_by_id(answer_id)
        await self._validate_applet_activity_access(applet_id, answer_schema.respondent_id)
        if activity_id:
            pk = self._generate_history_id(answer_schema.version)
            await ActivityHistoriesCRUD(self.session).get_by_id(pk(activity_id))

    async def _validate_submission_access(self, applet_id: uuid.UUID, submission_id: uuid.UUID, flow_id: uuid.UUID):
        answer = await self.get_submission_last_answer(submission_id, flow_id)
        if not answer:
            raise AnswerNotFoundError()
        await self._validate_applet_activity_access(applet_id, answer.respondent_id)

    async def get_flow_submission(
        self,
        applet_id: uuid.UUID,
        flow_id: uuid.UUID,
        submit_id: uuid.UUID,
    ) -> FlowSubmissionDetails:
        # TODO properly merge to multiinformant using subject ids
        allowed_respondents = await self._get_allowed_respondents(applet_id)

        repository = AnswersCRUD(self.answer_session)
        answers = await repository.get_list(
            applet_id=applet_id,
            flow_id=flow_id,
            submit_id=submit_id,
            respondent_ids=allowed_respondents,
        )
        if not answers:
            raise AnswerNotFoundError()

        activity_hist_ids = set()

        answer_result: list[ActivityAnswer] = []

        for answer in answers:
            answer_result.append(
                ActivityAnswer(
                    **answer.dict(exclude={"migrated_data"}),
                    **answer.answer_item.dict(
                        include={
                            "user_public_key",
                            "answer",
                            "events",
                            "item_ids",
                            "identifier",
                            "migrated_data",
                            "end_datetime",
                        }
                    ),
                )
            )
            activity_hist_ids.add(answer.activity_history_id)

        flow_history_id = answers[0].flow_history_id
        assert flow_history_id

        flows = await FlowsHistoryCRUD(self.session).load_full([flow_history_id])
        assert flows

        submission = FlowSubmissionDetails(
            submission=FlowSubmission(
                submit_id=submit_id,
                flow_history_id=flow_history_id,
                applet_id=applet_id,
                version=answer_result[0].version,
                created_at=max([a.created_at for a in answer_result]),
                end_datetime=max([a.end_datetime for a in answer_result]),
                answers=answer_result,
            ),
            flow=flows[0],
        )

        return submission

    async def add_answer_note(
        self,
        applet_id: uuid.UUID,
        answer_id: uuid.UUID,
        activity_id: uuid.UUID,
        note: str,
    ) -> AnswerNoteSchema:
        await self._validate_answer_access(applet_id, answer_id, activity_id)
        schema = AnswerNoteSchema(
            answer_id=answer_id,
            note=note,
            user_id=self.user_id,
            activity_id=activity_id,
        )
        note_schema = await AnswerNotesCRUD(self.session).save(schema)
        return note_schema

    async def get_note_list(
        self, applet_id: uuid.UUID, answer_id: uuid.UUID, activity_id: uuid.UUID, page: int, limit: int
    ) -> list[AnswerNoteDetail]:
        await self._validate_answer_access(applet_id, answer_id, activity_id)
        notes_crud = AnswerNotesCRUD(self.session)
        note_schemas = await notes_crud.get_by_answer_id(answer_id, activity_id, page, limit)
        user_ids = set(map(lambda n: n.user_id, note_schemas))
        users_crud = UsersCRUD(self.session)
        users = await users_crud.get_by_ids(user_ids)
        notes = await notes_crud.map_users_and_notes(note_schemas, users)
        return notes

    async def get_notes_count(self, answer_id: uuid.UUID, activity_id: uuid.UUID) -> int:
        return await AnswerNotesCRUD(self.session).get_count_by_answer_id(answer_id, activity_id)

    async def get_submission_notes_count(
        self, answer_id: uuid.UUID, activity_id: uuid.UUID, page: int, limit: int
    ) -> int:
        return await AnswerNotesCRUD(self.session).get_count_by_submission_id(answer_id, activity_id, page, limit)

    async def edit_answer_note(
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

    async def delete_answer_note(
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

    async def _get_full_assessment_info(self, applet_id: uuid.UUID, assessment_answer: AnswerItemSchema | None):
        assert self.user_id
        items_crud = ActivityItemHistoriesCRUD(self.session)
        last = items_crud.get_applets_assessments(applet_id)
        if assessment_answer:
            await self._validate_answer_access(applet_id, assessment_answer.answer_id)
            current = items_crud.get_assessment_activity_items(assessment_answer.assessment_activity_id)
            items_last, items_current = await asyncio.gather(last, current)
        else:
            items_last = await last
            items_current = None

        if len(items_last) == 0:
            return AssessmentAnswer(items=items_last)

        if items_last == items_current and assessment_answer:
            answer = AssessmentAnswer(
                reviewer_public_key=assessment_answer.user_public_key if assessment_answer else None,
                answer=assessment_answer.answer if assessment_answer else None,
                item_ids=assessment_answer.item_ids if assessment_answer else [],
                items=items_last,
                is_edited=assessment_answer.created_at != assessment_answer.updated_at  # noqa
                if assessment_answer
                else False,
                versions=[assessment_answer.assessment_activity_id],
            )
        else:
            if assessment_answer:
                versions = [
                    assessment_answer.assessment_activity_id,
                    items_last[0].activity_id,
                ]
            else:
                versions = [items_last[0].activity_id]
            answer = AssessmentAnswer(
                reviewer_public_key=assessment_answer.user_public_key if assessment_answer else None,
                answer=assessment_answer.answer if assessment_answer else None,
                item_ids=assessment_answer.item_ids if assessment_answer else [],
                items=items_current if assessment_answer else items_last,
                items_last=items_last if assessment_answer else None,
                is_edited=assessment_answer.created_at != assessment_answer.updated_at  # noqa
                if assessment_answer
                else False,
                versions=versions,
            )
        return answer

    async def get_assessment_by_answer_id(self, applet_id: uuid.UUID, answer_id: uuid.UUID) -> AssessmentAnswer:
        assert self.user_id
        assessment_answer = await AnswerItemsCRUD(self.answer_session).get_assessment(answer_id, self.user_id)
        assessment_answer_model = await self._get_full_assessment_info(applet_id, assessment_answer)
        return assessment_answer_model

    async def get_assessment_by_submit_id(self, applet_id: uuid.UUID, submit_id: uuid.UUID) -> AssessmentAnswer | None:
        assert self.user_id
        answer = await self.get_submission_last_answer(submit_id)
        if answer:
            assessment_answer = await AnswerItemsCRUD(self.answer_session).get_assessment(answer.id, self.user_id)
        else:
            # Submission without answer on assessments
            assessment_answer = None

        assessment_answer_model = await self._get_full_assessment_info(applet_id, assessment_answer)
        return assessment_answer_model

    async def get_reviews_by_answer_id(self, applet_id: uuid.UUID, answer_id: uuid.UUID) -> list[AnswerReview]:
        assert self.user_id

        await self._validate_answer_access(applet_id, answer_id)
        current_role = await AppletAccessCRUD(self.session).get_applets_priority_role(applet_id, self.user_id)
        reviewer_activity_version = await AnswerItemsCRUD(self.answer_session).get_assessment_activity_id(answer_id)
        if not reviewer_activity_version:
            return []

        activity_versions = [t[1] for t in reviewer_activity_version]
        activity_items = await ActivityItemHistoriesCRUD(self.session).get_by_activity_id_versions(activity_versions)

        reviews = await AnswerItemsCRUD(self.answer_session).get_reviews_by_answer_id(answer_id, activity_items)

        user_ids = [rev.respondent_id for rev in reviews]
        users = await UsersCRUD(self.session).get_by_ids(user_ids)
        results = []
        for schema in reviews:
            user = next(filter(lambda u: u.id == schema.respondent_id, users), None)
            current_activity_items = list(
                filter(
                    lambda i: i.activity_id == schema.assessment_activity_id,
                    activity_items,
                )
            )
            if not user:
                continue

            can_view = await self.can_view_current_review(user.id, current_role)
            results.append(
                AnswerReview(
                    id=schema.id,
                    reviewer_public_key=schema.user_public_key if can_view else None,
                    answer=schema.answer if can_view else None,
                    item_ids=schema.item_ids,
                    items=current_activity_items,
                    reviewer=dict(id=user.id, first_name=user.first_name, last_name=user.last_name),
                    created_at=schema.created_at,
                    updated_at=schema.updated_at,
                )
            )
        return results

    async def create_assessment_answer(
        self,
        applet_id: uuid.UUID,
        answer_id: uuid.UUID,
        schema: AssessmentAnswerCreate,
        submit_id: uuid.UUID | None = None,
    ):
        assert self.user_id

        await self._validate_answer_access(applet_id, answer_id)
        assessment = await AnswerItemsCRUD(self.answer_session).get_assessment(answer_id, self.user_id)
        if assessment:
            await AnswerItemsCRUD(self.answer_session).update(
                AnswerItemSchema(
                    id=assessment.id,
                    created_at=assessment.created_at,
                    updated_at=datetime.datetime.utcnow(),
                    answer_id=answer_id,
                    respondent_id=self.user_id,
                    answer=schema.answer,
                    item_ids=list(map(str, schema.item_ids)),
                    user_public_key=schema.reviewer_public_key,
                    is_assessment=True,
                    start_datetime=datetime.datetime.utcnow(),
                    end_datetime=datetime.datetime.utcnow(),
                    assessment_activity_id=schema.assessment_version_id,
                    reviewed_flow_submit_id=submit_id,
                )
            )
        else:
            now = datetime.datetime.utcnow()
            await AnswerItemsCRUD(self.answer_session).create(
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
                    assessment_activity_id=schema.assessment_version_id,
                    reviewed_flow_submit_id=submit_id,
                )
            )

    async def _validate_activity_for_assessment(self, activity_history_id: str):
        schema = await ActivityHistoriesCRUD(self.session).get_by_id(activity_history_id)

        if not schema.is_reviewable:
            raise ActivityIsNotAssessment()

    async def get_export_data(  # noqa: C901
        self,
        applet_id: uuid.UUID,
        query_params: QueryParams,
        skip_activities: bool = False,
    ) -> AnswerExport:
        assert self.user_id is not None

        access = await UserAppletAccessCRUD(self.session).get_by_roles(
            self.user_id,
            applet_id,
            [Role.OWNER, Role.MANAGER, Role.REVIEWER],
        )
        assessments_allowed = False
        allowed_respondents = None
        if not access:
            allowed_respondents = [self.user_id]
        elif access.role == Role.REVIEWER:
            if isinstance(access.reviewer_respondents, list) and len(access.reviewer_respondents) > 0:
                allowed_respondents = access.reviewer_respondents  # noqa: E501
            else:
                allowed_respondents = [self.user_id]
        else:  # [Role.OWNER, Role.MANAGER]
            assessments_allowed = True

        filters = query_params.filters
        if allowed_respondents:
            if _respondents := filters.get("respondent_ids"):
                filters["respondent_ids"] = list(set(allowed_respondents).intersection(_respondents))
            else:
                filters["respondent_ids"] = allowed_respondents

        repository = AnswersCRUD(self.answer_session)
        answers, total = await repository.get_applet_answers(
            applet_id,
            page=query_params.page,
            limit=query_params.limit,
            include_assessments=assessments_allowed,
            **filters,
        )

        if not answers:
            return AnswerExport()

        respondent_ids: set[uuid.UUID] = set()
        applet_assessment_ids = set()
        activity_hist_ids = set()
        flow_hist_ids = set()
        for answer in answers:
            respondent_ids.add(answer.respondent_id)  # type: ignore[arg-type]
            if answer.reviewed_answer_id:
                applet_assessment_ids.add(answer.applet_history_id)
            if answer.flow_history_id:
                flow_hist_ids.add(answer.flow_history_id)
            if answer.activity_history_id:
                activity_hist_ids.add(answer.activity_history_id)

        flows_coro = FlowsHistoryCRUD(self.session).get_by_id_versions(list(flow_hist_ids))
        user_map_coro = AppletAccessCRUD(self.session).get_respondent_export_data(applet_id, list(respondent_ids))

        coros_result = await asyncio.gather(
            flows_coro,
            user_map_coro,
            return_exceptions=True,
        )
        for res in coros_result:
            if isinstance(res, BaseException):
                raise res

        flows, user_map = coros_result
        flow_map = {flow.id_version: flow for flow in flows}  # type: ignore

        for answer in answers:
            # respondent data
            respondent = user_map[answer.respondent_id]  # type: ignore
            answer.respondent_secret_id = respondent.secret_id
            answer.respondent_email = respondent.email
            answer.is_manager = respondent.is_manager
            answer.legacy_profile_id = respondent.legacy_profile_id
            # flow data
            if flow_id := answer.flow_history_id:
                if flow := flow_map.get(flow_id):
                    answer.flow_name = flow.name

        repo_local = AnswersCRUD(self.session)
        activities_result = []
        if not skip_activities:
            activities, items = await asyncio.gather(
                ActivityHistoriesCRUD(self.session).get_by_history_ids(list(activity_hist_ids)),
                repo_local.get_item_history_by_activity_history(list(activity_hist_ids)),
            )

            activity_map = {activity.id_version: ActivityHistoryFull.from_orm(activity) for activity in activities}
            for item in items:
                activity = activity_map.get(item.activity_id)
                if activity:
                    activity.items.append(item)
            activities_result = list(activity_map.values())

        return AnswerExport(
            answers=answers,
            activities=activities_result,
            total_answers=total,
        )

    async def get_activity_identifiers(
        self, activity_id: uuid.UUID, respondent_id: uuid.UUID | None = None, answer_id: uuid.UUID | None = None
    ) -> list[Identifier]:
        act_hst_crud = ActivityHistoriesCRUD(self.session)
        await act_hst_crud.exist_by_activity_id_or_raise(activity_id)
        act_hst_list = await act_hst_crud.get_activities(activity_id, None)
        ids = set(map(lambda a: a.id_version, act_hst_list))
        identifiers = await AnswersCRUD(self.answer_session).get_identifiers_by_activity_id(
            ids, respondent_id, answer_id
        )
        results = []
        for identifier, key, migrated_data, answer_date in identifiers:
            if migrated_data and migrated_data.get("is_identifier_encrypted") is False:
                results.append(Identifier(identifier=identifier, last_answer_date=answer_date))
            else:
                results.append(Identifier(identifier=identifier, user_public_key=key, last_answer_date=answer_date))
        return results

    async def get_flow_identifiers(self, flow_id: uuid.UUID, respondent_id: uuid.UUID) -> list[Identifier]:
        # TODO properly merge to multiinformant
        identifier_data = await AnswersCRUD(self.answer_session).get_flow_identifiers(flow_id, respondent_id)
        result = [
            Identifier(
                identifier=row.identifier,
                last_answer_date=row.last_answer_date,
                user_public_key=row.user_public_key if row.is_encrypted else None,
            )
            for row in identifier_data
        ]

        return result

    async def get_activity_versions(
        self,
        activity_id: uuid.UUID,
    ) -> list[Version]:
        await ActivityHistoriesCRUD(self.session).exist_by_activity_id_or_raise(activity_id)
        return await AnswersCRUD(self.session).get_versions_by_activity_id(activity_id)

    async def get_activity_answers(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID,
        filters: QueryParams,
    ) -> list[AppletActivityAnswer]:
        versions = filters.filters.get("versions")

        if versions and isinstance(versions, str):
            versions = versions.split(",")

        activities = await ActivityHistoriesCRUD(self.session).get_activities(activity_id, versions)

        activity_items = await ActivityItemHistoriesCRUD(self.session).get_activity_items(activity_id, versions)
        id_versions = set(map(lambda act_hst: act_hst.id_version, activities))
        answers = await AnswerItemsCRUD(self.answer_session).get_applet_answers_by_activity_id(
            applet_id, id_versions, filters
        )

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
            answer_item.items = activity_item_map.get(answer.activity_history_id, [])
            activity_answer = AppletActivityAnswer.from_orm(answer_item)
            if answer_item.items:
                activity = activity_map[answer_item.items[0].activity_id]
                activity_answer.subscale_setting = activity.subscale_setting
            activity_answer.version = answer.version
            activity_answers.append(activity_answer)
        return activity_answers

    async def get_flow_submissions(
        self,
        flow_id: uuid.UUID,
        filters: QueryParams,
    ) -> tuple[FlowSubmissionsDetails, int]:
        submissions, total = await AnswersCRUD(self.answer_session).get_flow_submissions(
            flow_id, page=filters.page, limit=filters.limit, is_completed=True, **filters.filters
        )
        flow_history_ids = {s.flow_history_id for s in submissions}
        flows = []
        if flow_history_ids:
            flows = await FlowsHistoryCRUD(self.session).load_full(list(flow_history_ids))

        return FlowSubmissionsDetails(submissions=submissions, flows=flows), total

    async def get_answer_assessments_count(self, answer_ids: list[uuid.UUID]) -> dict[uuid.UUID, ReviewsCount]:
        answer_reviewers_t = await AnswerItemsCRUD(self.answer_session).get_reviewers_by_answers(answer_ids)
        answer_reviewers: dict[uuid.UUID, ReviewsCount] = {}
        for answer_id, reviewers in answer_reviewers_t:
            mine = 1 if self.user_id in reviewers else 0
            answer_reviewers[answer_id] = ReviewsCount(mine=mine, other=len(reviewers) - mine)
        return answer_reviewers

    async def get_submission_assessment_count(self, submission_ids: list[uuid.UUID]) -> dict[uuid.UUID, ReviewsCount]:
        answer_reviewers_t = await AnswerItemsCRUD(self.answer_session).get_reviewers_by_submission(submission_ids)
        answer_reviewers: dict[uuid.UUID, ReviewsCount] = {}
        for submission_id, reviewers in answer_reviewers_t:
            mine = 1 if self.user_id in reviewers else 0
            answer_reviewers[submission_id] = ReviewsCount(mine=mine, other=len(reviewers) - mine)
        return answer_reviewers

    async def get_summary_latest_report(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID,
        respondent_id: uuid.UUID,
    ) -> ReportServerResponse | None:
        respondent_exist = await UsersCRUD(self.session).exist_by_id(id_=respondent_id)
        if not respondent_exist:
            raise UserNotFound(f"No such respondent with id={respondent_id}.")

        await self._is_report_server_configured(applet_id)

        act_crud = ActivityHistoriesCRUD(self.session)
        activity_hsts = await act_crud.get_activities(activity_id, None)
        if not activity_hsts:
            activity_error_exception = ActivityDoeNotExist()
            activity_error_exception.message = f"No such activity with id=${activity_id}"
            raise activity_error_exception

        act_versions = set(map(lambda act_hst: act_hst.id_version, activity_hsts))
        answer = await AnswersCRUD(self.answer_session).get_latest_answer(applet_id, act_versions, respondent_id)
        if not answer:
            return None

        service = ReportServerService(self.session, arbitrary_session=self.answer_session)
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
        assert self.user_id
        act_hst_crud = ActivityHistoriesCRUD(self.session)
        activities = await act_hst_crud.get_last_histories_by_applet(applet_id=applet_id)
        activity_ver_ids = [activity.id_version for activity in activities]
        activity_ids_with_date = await AnswersCRUD(self.answer_session).get_submitted_activity_with_last_date(
            activity_ver_ids, respondent_id
        )
        submitted_activities: dict[str, datetime.datetime] = {}
        for activity_history_id, submit_date in activity_ids_with_date:
            activity_id = activity_history_id.split("_")[0]
            date = submitted_activities.get(activity_id)
            submitted_activities[activity_id] = max(submit_date, date) if date else submit_date
            submitted_activities[activity_history_id] = submit_date

        results = []
        for activity in activities:
            activity_history_answer_date = submitted_activities.get(
                activity.id_version, submitted_activities.get(str(activity.id))
            )
            results.append(
                SummaryActivity(
                    id=activity.id,
                    name=activity.name,
                    is_performance_task=activity.is_performance_task,
                    has_answer=bool(activity_history_answer_date),
                    last_answer_date=activity_history_answer_date,
                )
            )
        return results

    async def get_summary_activity_flows(
        self, applet_id: uuid.UUID, respondent_id: uuid.UUID | None
    ) -> list[SummaryActivityFlow]:
        assert self.user_id
        flow_crud = FlowsHistoryCRUD(self.session)
        answer_crud = AnswersCRUD(self.answer_session)
        flow_history_ids_with_date = await answer_crud.get_submitted_flows_with_last_date(applet_id, respondent_id)
        activity_flow_histories = await flow_crud.get_last_histories_by_applet(applet_id)

        submitted_activity_flows: dict[str, datetime.datetime] = {}
        for version_id, submit_date in flow_history_ids_with_date:
            flow_id = version_id.split("_")[0]
            date = submitted_activity_flows.get(flow_id)
            submitted_activity_flows[flow_id] = max(submit_date, date) if date else submit_date
            submitted_activity_flows[version_id] = submit_date

        results = []
        for flow_history in activity_flow_histories:
            flow_history_answer_date = submitted_activity_flows.get(
                flow_history.id_version, submitted_activity_flows.get(str(flow_history.id))
            )
            results.append(
                SummaryActivityFlow(
                    id=flow_history.id,
                    name=flow_history.name,
                    has_answer=bool(flow_history_answer_date),
                    last_answer_date=flow_history_answer_date,
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
        persons = await UserAppletAccessCRUD(self.session).get_responsible_persons(applet_id, self.user_id)
        alert_schemas = []

        for person in persons:
            for raw_alert in raw_alerts:
                alert_schemas.append(
                    AlertSchema(
                        user_id=person.id,
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
        await self.send_alert_mail(persons)

    async def get_completed_answers_data(
        self, applet_id: uuid.UUID, version: str, from_date: datetime.date
    ) -> AppletCompletedEntities:
        assert self.user_id
        result = await AnswersCRUD(self.answer_session).get_completed_answers_data(
            applet_id,
            version,
            self.user_id,
            from_date,
        )
        return result

    async def get_completed_answers_data_list(
        self,
        applets_version_map: dict[uuid.UUID, str],
        from_date: datetime.date,
    ) -> list[AppletCompletedEntities]:
        assert self.user_id
        result = await AnswersCRUD(self.answer_session).get_completed_answers_data_list(
            applets_version_map,
            self.user_id,
            from_date,
        )
        return result

    async def is_answers_uploaded(self, applet_id: uuid.UUID, activity_id: str, created_at: int) -> bool:
        answers = await AnswersCRUD(self.answer_session).get_by_applet_activity_created_at(
            applet_id, activity_id, created_at
        )
        if not answers:
            return False

        return True

    @staticmethod
    async def send_alert_mail(users: List[UserSchema]):
        domain = os.environ.get("ADMIN_DOMAIN", "")
        mail_service = MailingService()
        schemas = pydantic.parse_obj_as(List[User], users)
        email_list = [schema.email_encrypted for schema in schemas]
        return await mail_service.send(
            MessageSchema(
                recipients=email_list,
                subject="Response alert",
                body=mail_service.get_template(path="response_alert_en", domain=domain),
            )
        )

    @classmethod
    def _is_public_key_match(cls, answer_id, stored_public_key, generated_public_key) -> bool:
        if not stored_public_key:
            logger.error(
                f'Reencryption:  Answer item "{answer_id}": wrong public key, skip'  # noqa: E501
            )
        try:
            stored_public_key = json.loads(stored_public_key)
        except JSONDecodeError as e:
            logger.error(
                f'Reencryption:  Answer item "{answer_id}": wrong public key, skip'  # noqa: E501
            )
            logger.exception(str(e))
            return False

        if stored_public_key != generated_public_key:
            logger.error(
                f'Reencryption: Answer item "{answer_id}": public key doesn\'t match, skip'  # noqa: E501
            )
            return False

        return True

    async def reencrypt_user_answers(
        self,
        applet_id: uuid.UUID,
        user_id: uuid.UUID,
        page=1,
        limit=1000,
        *,
        old_public_key: list,
        new_public_key: list,
        decryptor: "AnswerEncryptor",
        encryptor: "AnswerEncryptor",
    ) -> int:
        logger.debug(f'Reencryption: Start reencrypt_user_answers for "{applet_id}"')
        repository = AnswersCRUD(self.answer_session)
        answers = await repository.get_applet_user_answer_items(applet_id, user_id, page, limit)
        count = len(answers)
        if not count:
            return 0

        data_to_update: list[AnswerItemDataEncrypted] = []
        for answer in answers:
            if not self._is_public_key_match(answer.id, answer.user_public_key, old_public_key):
                continue

            try:
                encrypted_answer = encryptor.encrypt(decryptor.decrypt(answer.answer))
                encrypted_events, encrypted_identifier = None, None
                if answer.events:
                    encrypted_events = encryptor.encrypt(decryptor.decrypt(answer.events))
                if answer.identifier:
                    if answer.migrated_data and answer.migrated_data.get("is_identifier_encrypted") is False:
                        encrypted_identifier = encrypted_identifier
                    else:
                        encrypted_identifier = encryptor.encrypt(decryptor.decrypt(answer.identifier))

                data_to_update.append(
                    AnswerItemDataEncrypted(
                        id=answer.id,
                        answer=encrypted_answer,
                        events=encrypted_events,
                        identifier=encrypted_identifier,
                    )
                )
            except EncryptionError as e:
                logger.error(
                    f'Reencryption: Skip answer item "{answer.id}": cannot decrypt answer'  # noqa: E501
                )
                logger.exception(str(e))
                continue

        if data_to_update:
            await repository.update_encrypted_fields(json.dumps(new_public_key), data_to_update)

        return count

    async def fill_last_activity_workspace_respondent(
        self,
        respondents: list[WorkspaceRespondent],
        applet_id: uuid.UUID | None = None,
    ) -> list[WorkspaceRespondent]:
        respondent_ids = [respondent.id for respondent in respondents]
        result = await AnswersCRUD(self.answer_session).get_last_activity(respondent_ids, applet_id)
        for respondent in respondents:
            respondent.last_seen = result.get(respondent.id)
        return respondents

    async def fill_last_activity_respondent_info(
        self,
        respondent_id: uuid.UUID,
        applet_id: uuid.UUID,
    ) -> dict[uuid.UUID, datetime.datetime]:
        result = await AnswersCRUD(self.answer_session).get_last_activity([respondent_id], applet_id)
        return result

    async def get_answer_assessment_by_id(
        self, assessment_id: uuid.UUID, answer_id: uuid.UUID
    ) -> AssessmentItem | None:
        schema = await AnswerItemsCRUD(self.answer_session).get_answer_assessment(assessment_id, answer_id)
        return AssessmentItem.from_orm(schema) if schema else None

    async def delete_assessment(self, assessment_id: uuid.UUID):
        return await AnswerItemsCRUD(self.answer_session).delete_assessment(assessment_id)

    async def can_view_current_review(self, reviewer_id: uuid.UUID, role: Role | None):
        if not role:
            return False

        if role == Role.REVIEWER and reviewer_id == self.user_id:
            return True
        elif role in [Role.MANAGER, Role.OWNER]:
            return True
        return False

    async def get_submission_last_answer(
        self, submit_id: uuid.UUID, flow_id: uuid.UUID | None = None
    ) -> AnswerSchema | None:
        return await AnswersCRUD(self.answer_session).get_last_answer_in_flow(submit_id, flow_id)

    async def add_submission_note(
        self,
        applet_id: uuid.UUID,
        submission_id: uuid.UUID,
        flow_id: uuid.UUID,
        note: str,
    ):
        answer = await self.get_submission_last_answer(submission_id)
        if not answer:
            raise AnswerNotFoundError()
        await self._validate_applet_activity_access(applet_id, answer)
        schema = AnswerNoteSchema(
            answer_id=answer.id, note=note, user_id=self.user_id, activity_flow_id=flow_id, submission_id=submission_id
        )
        note_schema = await AnswerNotesCRUD(self.session).save(schema)
        return note_schema

    async def get_submission_note_list(
        self,
        applet_id: uuid.UUID,
        submission_id: uuid.UUID,
        flow_id: uuid.UUID,
        page: int,
        limit: int,
    ) -> list[AnswerNoteDetail]:
        await self._validate_submission_access(applet_id, submission_id, flow_id)
        notes_crud = AnswerNotesCRUD(self.session)
        note_schemas = await notes_crud.get_by_submission_id(submission_id, flow_id, page, limit)
        user_ids = set(map(lambda n: n.user_id, note_schemas))
        users_crud = UsersCRUD(self.session)
        users = await users_crud.get_by_ids(user_ids)
        notes = await notes_crud.map_users_and_notes(note_schemas, users)
        return notes

    async def edit_submission_note(
        self,
        applet_id: uuid.UUID,
        submission_id: uuid.UUID,
        flow_id: uuid.UUID,
        note_id: uuid.UUID,
        note: str,
    ):
        await self._validate_submission_access(applet_id, submission_id, flow_id)
        await self._validate_note_access(note_id)
        await AnswerNotesCRUD(self.session).update_note_by_id(note_id, note)

    async def delete_submission_note(
        self,
        applet_id: uuid.UUID,
        submission_id: uuid.UUID,
        flow_id: uuid.UUID,
        note_id: uuid.UUID,
    ):
        await self._validate_submission_access(applet_id, submission_id, flow_id)
        await self._validate_note_access(note_id)
        await AnswerNotesCRUD(self.session).delete_note_by_id(note_id)


class ReportServerService:
    def __init__(self, session, arbitrary_session=None):
        self.session = session
        self._answers_session = arbitrary_session

    @property
    def answers_session(self):
        return self._answers_session if self._answers_session else self.session

    async def is_reportable(self, answer: AnswerSchema, is_single_report_flow=False) -> bool:
        """Check is report available for answer or not.

        First check applet report related fields. All fields must be filled.
        Second check activities report related fields. If it is flow single
        report then one of activities must be reportable (have filled all
        reportable fields). If it is not flow single report then answers
        activity must have filled reportable fields.
        """
        # It is simpler to use AppletHistoryService to get all required data.
        # It allows to reduce repeatable logic for single report flow and
        # for general case.
        applet = await AppletHistoryService(self.session, answer.applet_id, answer.version).get_full()
        _is_reportable = False
        if not (applet.report_server_ip and applet.report_public_key and applet.report_recipients):
            return _is_reportable

        flow_activities = []
        if is_single_report_flow:
            flow = next(i for i in applet.activity_flows if i.id_version == answer.flow_history_id)
            flow_activities = [i.activity_id for i in flow.items]
        for activity in applet.activities:
            if (
                activity.scores_and_reports is not None
                and activity.scores_and_reports.generate_report
                and activity.scores_and_reports.reports
                and (answer.activity_history_id in flow_activities or answer.activity_history_id == activity.id_version)
            ):
                _is_reportable = True
                break
        return _is_reportable

    async def is_flows_single_report(self, answer_id: uuid.UUID) -> bool:
        """
        Whether check to send flow reports in a single or multiple request
        """
        answer = await AnswersCRUD(self.answers_session).get_by_id(answer_id)
        # ActivityFlow a stored in local db
        is_single_report = await AnswersCRUD(self.session).is_single_report_flow(answer.flow_history_id)
        return is_single_report

    async def is_flow_finished(self, submit_id: uuid.UUID, answer_id: uuid.UUID) -> bool:
        answers = await AnswersCRUD(self.answers_session).get_by_submit_id(submit_id, answer_id)
        if not answers:
            return False
        initial_answer = answers[0]

        applet = await AppletsCRUD(self.session).get_by_id(initial_answer.applet_id)
        applet_full = await self._prepare_applet_data(
            initial_answer.applet_id, initial_answer.version, applet.encryption
        )
        activity_id, _ = initial_answer.activity_history_id.split("_")
        flow_id = ""
        if initial_answer.flow_history_id:
            flow_id, _ = initial_answer.flow_history_id.split("_")

        return self._is_activity_last_in_flow(applet_full, activity_id, flow_id)

    async def create_report(
        self, submit_id: uuid.UUID, answer_id: uuid.UUID | None = None
    ) -> ReportServerResponse | None:
        answers = await AnswersCRUD(self.answers_session).get_by_submit_id(submit_id, answer_id)
        if not answers:
            return None
        applet_id_version: str = answers[0].applet_history_id
        available_activities = await ActivityHistoriesCRUD(self.session).get_activity_id_versions_for_report(
            applet_id_version
        )
        answers_for_report = [i for i in answers if i.activity_history_id in available_activities]
        # If answers only on performance tasks
        if not answers_for_report:
            return None
        answer_map = dict((answer.id, answer) for answer in answers_for_report)
        initial_answer = answers_for_report[0]

        applet = await AppletsCRUD(self.session).get_by_id(initial_answer.applet_id)
        user_info = await self._get_user_info(initial_answer.respondent_id, initial_answer.applet_id)
        applet_full = await self._prepare_applet_data(
            initial_answer.applet_id,
            initial_answer.version,
            applet.encryption,
            non_performance=True,
        )

        encryption = ReportServerEncryption(applet.report_public_key)
        responses, user_public_keys = await self._prepare_responses(answer_map)

        data = dict(
            responses=responses,
            userPublicKeys=user_public_keys,
            userPublicKey=user_public_keys[0],
            now=datetime.datetime.utcnow().strftime("%x"),
            user=user_info,
            applet=applet_full,
        )
        encrypted_data = encryption.encrypt(data)

        activity_id, _ = initial_answer.activity_history_id.split("_")
        flow_id = ""
        if initial_answer.flow_history_id:
            flow_id, _ = initial_answer.flow_history_id.split("_")

        url = "{}/send-pdf-report?activityId={}&activityFlowId={}".format(
            applet.report_server_ip.rstrip("/"), activity_id, flow_id
        )

        async with aiohttp.ClientSession() as session:
            logger.info(f"Sending request to the report server {url}.")
            start = time.time()
            async with session.post(
                url,
                json=dict(payload=encrypted_data),
            ) as resp:
                duration = time.time() - start
                if resp.status == 200:
                    logger.info(f"Successful request in {duration:.1f} seconds.")
                    response_data = await resp.json()
                    return ReportServerResponse(**response_data)
                else:
                    logger.error(f"Failed request in {duration:.1f} seconds.")
                    error_message = await resp.text()
                    raise ReportServerError(message=error_message)

    def _is_activity_last_in_flow(self, applet_full: dict, activity_id: str | None, flow_id: str | None) -> bool:
        if "activityFlows" not in applet_full or "activities" not in applet_full or not activity_id or not flow_id:
            return False

        flows = applet_full["activityFlows"]
        flow = next((f for f in flows if str(f["id"]) == flow_id), None)
        if not flow or "items" not in flow or len(flow["items"]) == 0:
            return False

        return activity_id == flow["items"][-1]["activityId"].split("_")[0]

    async def _prepare_applet_data(
        self,
        applet_id: uuid.UUID,
        version: str,
        encryption: dict,
        non_performance: bool = False,
    ):
        applet_full = await AppletHistoryService(self.session, applet_id, version).get_full(non_performance)
        applet_full.encryption = Encryption(**encryption)
        return applet_full.dict(by_alias=True)

    async def _get_user_info(self, respondent_id: uuid.UUID, applet_id: uuid.UUID):
        access = await UserAppletAccessCRUD(self.session).get(respondent_id, applet_id, Role.RESPONDENT)
        assert access
        return dict(
            firstName=access.meta.get("firstName"),
            lastName=access.meta.get("lastName"),
            nickname=access.nickname,
            secretId=access.meta.get("secretUserId"),
        )

    async def _prepare_responses(self, answers_map: dict[uuid.UUID, AnswerSchema]) -> tuple[list[dict], list[str]]:
        answer_items = await AnswerItemsCRUD(self.answers_session).get_respondent_submits_by_answer_ids(
            list(answers_map.keys())
        )

        responses = list()
        for answer_item in answer_items:
            answer = answers_map[answer_item.answer_id]
            activity_id, version = answer.activity_history_id.split("_")
            responses.append(dict(activityId=activity_id, answer=answer_item.answer))
        return responses, [ai.user_public_key for ai in answer_items]


class ReportServerEncryption:
    _rate = 0.58

    def __init__(self, key: str):
        self.encryption = load_pem_public_key(key.encode(), backend=default_backend())

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


class AnswerEncryptor:
    def __init__(self, key: list | bytes):
        if isinstance(key, list):
            key = bytes(key)
        self.key: bytes = key

    def encrypt(self, data: str, iv: bytes | None = None):
        try:
            ct, iv = encrypt_cbc(self.key, data.encode("utf-8"), iv)
        except Exception as e:
            raise EncryptionError("Cannot encrypt answer data") from e
        return f"{iv.hex()}:{ct.hex()}"

    def decrypt(self, encrypted_data: str) -> str:
        """
        @param encrypted_data: data in hex format "iv:text"
        """
        try:
            iv_hex, text_hex = encrypted_data.split(":", 1)
            data = bytes.fromhex(text_hex)
            iv = bytes.fromhex(iv_hex)

            return decrypt_cbc(self.key, data, iv).decode("utf-8")
        except Exception as e:
            raise EncryptionError("Cannot decrypt answer data") from e
