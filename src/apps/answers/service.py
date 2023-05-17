import datetime
import uuid

from apps.activities.domain.activity_full import PublicActivityItemFull
from apps.activities.services import ActivityHistoryService
from apps.activities.services.activity_item_history import (
    ActivityItemHistoryService,
)
from apps.activity_flows.service.flow_item_history import (
    FlowItemHistoryService,
)
from apps.answers.crud import AnswerActivityItemsCRUD, AnswerFlowItemsCRUD
from apps.answers.crud.answers import AnswersCRUD
from apps.answers.crud.notes import AnswerNotesCRUD
from apps.answers.db.schemas import (
    AnswerActivityItemsSchema,
    AnswerFlowItemsSchema,
    AnswerNoteSchema,
    AnswerSchema,
)
from apps.answers.domain import (
    ActivityAnswer,
    ActivityItemAnswer,
    AnswerDate,
    AnsweredAppletActivity,
    AnswerNoteDetail,
    AppletAnswerCreate,
)
from apps.answers.errors import (
    AnswerAccessDeniedError,
    AnswerNoteAccessDeniedError,
    FlowDoesNotHaveActivity,
    UserDoesNotHavePermissionError,
)
from apps.applets.crud import AppletsCRUD
from apps.applets.service import AppletHistoryService
from apps.shared.query_params import QueryParams
from apps.workspaces.crud.applet_access import AppletAccessCRUD
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.user_applet_access import UserAppletAccessService


class AnswerService:
    def __init__(self, session, user_id: uuid.UUID | None):
        self.user_id = user_id
        self.session = session

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

    async def _validate_answer(self, activity_answer: AppletAnswerCreate):
        if activity_answer.flow_id:
            activity_id_version = (
                f"{activity_answer.activity_id}_{activity_answer.version}"
            )
            flow_activity_ids = await FlowItemHistoryService(
                self.session,
                activity_answer.applet_id,
                activity_answer.version,
            ).get_activity_ids_by_flow_id(activity_answer.flow_id)
            if activity_id_version not in flow_activity_ids:
                raise FlowDoesNotHaveActivity()
        await ActivityHistoryService(
            self.session, activity_answer.applet_id, activity_answer.version
        ).get_by_id(activity_answer.activity_id)

    async def _validate_applet_for_anonymous_response(
            self, applet_id: uuid.UUID, version: str
    ):
        await AppletHistoryService(self.session, applet_id, version).get()
        # TODO: validate applet for anonymous answer

    async def _validate_applet_for_user_response(self, applet_id: uuid.UUID):
        assert self.user_id

        roles = await UserAppletAccessService(
            self.session, self.user_id, applet_id
        ).get_roles()
        if not roles:
            raise UserDoesNotHavePermissionError()

    async def _create_answer(self, applet_answer: AppletAnswerCreate):
        created_at = datetime.datetime.now()
        if applet_answer.created_at:
            created_at = datetime.datetime.fromtimestamp(
                applet_answer.created_at
            )
        applet_id_version = (
            f"{applet_answer.applet_id}_{applet_answer.version}"
        )
        activity_id_version = (
            f"{applet_answer.activity_id}_{applet_answer.version}"
        )
        answer_groups: dict[str, AnswerSchema] = dict()
        activity_item_answer_schemas = []
        flow_item_answer_schemas = []
        for answer in applet_answer.answers:
            activity_item_id_version = (
                f"{answer.activity_item_id}_{applet_answer.version}"
            )
            if applet_answer.flow_id:
                flow_id_version = (
                    f"{applet_answer.flow_id}_{applet_answer.version}"
                )
                answer_key = (
                    f"{applet_answer.flow_id}_{applet_answer.activity_id}"
                )
                answer_group = answer_groups.get(
                    answer_key,
                    AnswerSchema(
                        id=uuid.uuid4(),
                        created_at=created_at,
                        applet_id=applet_answer.applet_id,
                        flow_history_id=flow_id_version,
                        activity_history_id=activity_id_version,
                        respondent_id=self.user_id,
                    ),
                )
                answer_groups[answer_key] = answer_group

                flow_item_answer_schemas.append(
                    AnswerFlowItemsSchema(
                        id=uuid.uuid4(),
                        answer_id=answer_group.id,
                        respondent_id=self.user_id,
                        applet_id=applet_answer.applet_id,
                        answer=answer.answer.dict(),
                        applet_history_id=applet_id_version,
                        flow_history_id=flow_id_version,
                        activity_history_id=activity_id_version,
                        activity_item_history_id=activity_item_id_version,
                    )
                )
            else:
                answer_key = str(applet_answer.activity_id)
                answer_group = answer_groups.get(
                    answer_key,
                    AnswerSchema(
                        id=uuid.uuid4(),
                        created_at=created_at,
                        applet_id=applet_answer.applet_id,
                        flow_history_id=None,
                        activity_history_id=activity_id_version,
                        respondent_id=self.user_id,
                    ),
                )
                answer_groups[answer_key] = answer_group

                activity_item_answer_schemas.append(
                    AnswerActivityItemsSchema(
                        id=uuid.uuid4(),
                        answer_id=answer_group.id,
                        respondent_id=self.user_id,
                        applet_id=applet_answer.applet_id,
                        answer=answer.answer.dict(),
                        applet_history_id=applet_id_version,
                        activity_history_id=activity_id_version,
                        activity_item_history_id=activity_item_id_version,
                    )
                )

        if not answer_groups:
            answer_groups[uuid.uuid4().hex] = AnswerSchema(
                id=uuid.uuid4(),
                created_at=created_at,
                applet_id=applet_answer.applet_id,
                flow_history_id=applet_answer.flow_id,
                activity_history_id=activity_id_version,
                respondent_id=self.user_id,
            )
        await AnswersCRUD(self.session).create_many(
            list(answer_groups.values())
        )

        if activity_item_answer_schemas:
            await AnswerActivityItemsCRUD(self.session).create_many(
                activity_item_answer_schemas
            )
        elif flow_item_answer_schemas:
            await AnswerFlowItemsCRUD(self.session).create_many(
                flow_item_answer_schemas
            )

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
            applet = await AppletsCRUD().get_by_id(applet_id)
            activities = await ActivityHistoryService(
                self.session, applet_id, applet.version
            ).list()
            for activity in activities:
                activity_map[str(activity.id)] = AnsweredAppletActivity(
                    id=activity.id, name=activity.name
                )
        else:
            for answer in answers:
                _, version = answer.activity_history_id.split("_")

                activities = await ActivityHistoryService(
                    self.session, applet_id, version
                ).list()
                for activity in activities:
                    activity_map[str(activity.id)] = AnsweredAppletActivity(
                        id=activity.id, name=activity.name
                    )
        for answer in answers:
            activity_id, version = answer.activity_history_id.split("_")
            activity_map[activity_id].answer_dates.append(
                AnswerDate(created_at=answer.created_at, answer_id=answer.id)
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
            self, applet_id: uuid.UUID, answer_id: uuid.UUID
    ) -> ActivityAnswer:
        await self._validate_answer_access(applet_id, answer_id)
        item_answers = await AnswerActivityItemsCRUD(
            self.session
        ).get_by_answer_id(answer_id)

        flow_item_answers = await AnswerFlowItemsCRUD(
            self.session
        ).get_by_answer_id(answer_id)

        schema = await AnswersCRUD(self.session).get_by_id(answer_id)
        activity_id, version = schema.activity_history_id.split("_")
        activity_items = await ActivityItemHistoryService(
            self.session, applet_id, version
        ).get_by_activity_id(activity_id)

        item_answer_map = dict()
        for item_answer in item_answers:
            item_answer_map[
                item_answer.activity_item_history_id
            ] = item_answer.answer

        for flow_item_answer in flow_item_answers:
            item_answer_map[
                flow_item_answer.activity_item_history_id
            ] = flow_item_answer.answer

        answer = ActivityAnswer()
        for activity_item in activity_items:
            answer.activity_item_answers.append(
                ActivityItemAnswer(
                    type=activity_item.response_type,
                    activity_item=PublicActivityItemFull.from_orm(
                        activity_item
                    ),
                    answer=item_answer_map.get(activity_item.id_version),
                )
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
            self, applet_id: uuid.UUID, answer_id: uuid.UUID, note: str
    ):
        await self._validate_answer_access(applet_id, answer_id)
        schema = AnswerNoteSchema(
            answer_id=answer_id, note=note, user_id=self.user_id
        )
        await AnswerNotesCRUD(self.session).save(schema)

    async def get_note_list(
            self,
            applet_id: uuid.UUID,
            answer_id: uuid.UUID,
            query_params: QueryParams,
    ) -> list[AnswerNoteDetail]:
        await self._validate_answer_access(applet_id, answer_id)
        notes = await AnswerNotesCRUD(self.session).get_by_answer_id(
            answer_id, query_params
        )
        return notes

    async def get_notes_count(
            self,
            answer_id: uuid.UUID,
    ) -> int:
        return await AnswerNotesCRUD(self.session).get_count_by_answer_id(
            answer_id
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
            self, applet_id: uuid.UUID, answer_id: uuid.UUID,
            note_id: uuid.UUID
    ):
        await self._validate_answer_access(applet_id, answer_id)
        await self._validate_note_access(note_id)
        await AnswerNotesCRUD(self.session).delete_note_by_id(note_id)

    async def _validate_note_access(self, note_id: uuid.UUID):
        note = await AnswerNotesCRUD(self.session).get_by_id(note_id)
        if note.user_id != self.user_id:
            raise AnswerNoteAccessDeniedError()
