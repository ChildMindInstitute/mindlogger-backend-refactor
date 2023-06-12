import asyncio
import datetime
import uuid
from collections import defaultdict

from apps.activities.crud import (
    ActivityHistoriesCRUD,
    ActivityItemHistoriesCRUD,
)
from apps.activities.domain.activity_history import ActivityHistoryFull
from apps.activities.services import ActivityHistoryService
from apps.activities.services.activity_item_history import (
    ActivityItemHistoryService,
)
from apps.activity_flows.crud import FlowItemHistoriesCRUD
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
    AnswerDate,
    AnsweredAppletActivity,
    AnswerExport,
    AnswerNoteDetail,
    AnswerReview,
    AppletActivityAnswer,
    AppletAnswerCreate,
    AssessmentAnswer,
    AssessmentAnswerCreate,
)
from apps.answers.errors import (
    ActivityDoesNotHaveItem,
    ActivityIsNotAssessment,
    AnswerAccessDeniedError,
    AnswerNoteAccessDeniedError,
    FlowDoesNotHaveActivity,
    NonPublicAppletError,
    UserDoesNotHavePermissionError,
)
from apps.applets.crud import AppletsCRUD
from apps.applets.service import AppletHistoryService
from apps.shared.query_params import QueryParams
from apps.workspaces.crud.applet_access import AppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


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
        activity_flow_map: dict[str, str] = dict()
        item_activity_map: dict[str, str] = dict()
        get_pk = self._generate_history_id(applet_answer.version)
        if not applet_answer.answer:
            return
        activity_id = applet_answer.activity_id
        if applet_answer.flow_id:
            activity_flow_map[get_pk(activity_id)] = get_pk(
                applet_answer.flow_id
            )

        for activity_item_id in applet_answer.answer.item_ids or []:
            activity_id_version = item_activity_map.get(
                get_pk(activity_item_id)
            )
            if activity_id_version and activity_id_version != get_pk(
                applet_answer.activity_id
            ):
                raise ValueError(
                    "Same activity item can not have several activity"
                )
            item_activity_map[get_pk(activity_item_id)] = get_pk(
                applet_answer.activity_id
            )

        activity_item_histories = []
        flow_item_histories = []
        if item_activity_map:
            activity_item_histories = await ActivityItemHistoriesCRUD(
                self.session
            ).get_by_id_versions(list(item_activity_map.keys()))
        if activity_flow_map:
            flow_item_histories = await FlowItemHistoriesCRUD(
                self.session
            ).get_by_map(activity_flow_map)

        for activity_item_history in activity_item_histories:
            activity_id_version = item_activity_map[
                activity_item_history.id_version
            ]
            if activity_id_version != activity_item_history.activity_id:
                raise ActivityDoesNotHaveItem()

            item_activity_map.pop(activity_item_history.id_version)

        if len(item_activity_map) != 0:
            raise ValueError("Does not exists")

        for flow_item_history in flow_item_histories:
            flow_id_version = activity_flow_map[flow_item_history.activity_id]
            if flow_id_version != flow_item_history.activity_flow_id:
                raise FlowDoesNotHaveActivity()

            activity_flow_map.pop(flow_item_history.activity_id)

        if len(activity_flow_map) != 0:
            raise ValueError("Does not exists")

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

    async def applet_activities(
        self,
        applet_id: uuid.UUID,
        respondent_id: uuid.UUID,
        created_date: datetime.date,
    ) -> list[AnsweredAppletActivity]:
        await self._validate_applet_activity_access(applet_id, respondent_id)
        answers = await AnswersCRUD(
            self.session
        ).get_respondents_answered_activities_by_applet_id(
            respondent_id, applet_id, created_date
        )
        activity_map: dict[str, AnsweredAppletActivity] = dict()
        if not answers:
            applet = await AppletsCRUD(self.session).get_by_id(applet_id)
            activities = await ActivityHistoryService(
                self.session, applet_id, applet.version
            ).activities_list()
            for activity in activities:
                activity_map[str(activity.id)] = AnsweredAppletActivity(
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
                    activity_map[str(activity.id)] = AnsweredAppletActivity(
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
        await self._validate_answer_access(applet_id, answer_id)

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
        self, applet_id: uuid.UUID, answer_id: uuid.UUID
    ):
        answer_schema = await AnswersCRUD(self.session).get_by_id(answer_id)
        await self._validate_applet_activity_access(
            applet_id, answer_schema.respondent_id
        )

    async def add_note(
        self,
        applet_id: uuid.UUID,
        answer_id: uuid.UUID,
        activity_id: uuid.UUID,
        note: str,
    ):
        await self._validate_answer_access(applet_id, answer_id)
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
        await self._validate_answer_access(applet_id, answer_id)
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
        note_id: uuid.UUID,
        note: str,
    ):
        await self._validate_answer_access(applet_id, answer_id)
        await self._validate_note_access(note_id)
        await AnswerNotesCRUD(self.session).update_note_by_id(note_id, note)

    async def delete_note(
        self, applet_id: uuid.UUID, answer_id: uuid.UUID, note_id: uuid.UUID
    ):
        await self._validate_answer_access(applet_id, answer_id)
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
            != assessment_answer.updated_at
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
        filters: QueryParams,
    ) -> list[str]:
        return await AnswersCRUD(self.session).get_identifiers_by_activity_id(
            activity_id, filters
        )

    async def get_activity_versions(
        self,
        activity_id: uuid.UUID,
        filters: QueryParams,
    ) -> list[str]:
        return await AnswersCRUD(self.session).get_versions_by_activity_id(
            activity_id, filters
        )

    async def get_activity_answers(
        self,
        applet_id: uuid.UUID,
        activity_id: uuid.UUID,
        filters: QueryParams,
    ) -> list[AppletActivityAnswer]:
        versions = filters.filters.get("versions")
        if isinstance(versions, str):
            versions = versions.split(",")
        activity_items = await ActivityItemHistoriesCRUD(
            self.session
        ).get_activity_items(activity_id, versions)
        answers = await AnswerItemsCRUD(
            self.session
        ).get_applet_answers_by_activity_id(applet_id, activity_id, filters)

        activity_item_map = defaultdict(list)
        for activity_item in activity_items:
            activity_item_map[activity_item.activity_id].append(activity_item)

        activity_answers = list()
        for answer, answer_item in answers:
            answer_item.items = activity_item_map.get(
                answer.activity_history_id
            )
            activity_answer = AppletActivityAnswer.from_orm(answer_item)
            activity_answer.version = answer.version
            activity_answers.append(activity_answer)

        return activity_answers
