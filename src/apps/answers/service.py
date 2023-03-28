import json
import uuid

from apps.activities.services.activity_item_history import (
    ActivityItemHistoryService,
)
from apps.activity_flows.service.flow_item_history import (
    FlowItemHistoryService,
)
from apps.answers.crud import AnswerActivityItemsCRUD, AnswerFlowItemsCRUD
from apps.answers.db.schemas import (
    AnswerActivityItemsSchema,
    AnswerFlowItemsSchema,
)
from apps.answers.domain import AppletAnswerCreate
from apps.answers.errors import (
    AnswerIsNotFull,
    FlowDoesNotHaveActivity,
    UserDoesNotHavePermissionError,
)
from apps.applets.service import AppletHistoryService
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

        activity_items = await ActivityItemHistoryService(
            self.session, activity_answer.applet_id, activity_answer.version
        ).get_by_activity_id(activity_answer.activity_id)

        answer_map = dict()

        for answer in activity_answer.answers:
            answer_map[answer.activity_item_id] = answer

        for activity_item in activity_items:
            required = False
            required |= activity_item.config.get("response_required", False)
            required |= activity_item.skippable_item
            if required and activity_item.id not in answer_map:
                raise AnswerIsNotFull()

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
        applet_id_version = (
            f"{applet_answer.applet_id}_{applet_answer.version}"
        )
        activity_id_version = (
            f"{applet_answer.activity_id}_{applet_answer.version}"
        )
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
                flow_item_answer_schemas.append(
                    AnswerFlowItemsSchema(
                        id=uuid.uuid4(),
                        respondent_id=self.user_id,
                        applet_id=applet_answer.applet_id,
                        answer=json.dumps(answer.answer.dict()),
                        applet_history_id=applet_id_version,
                        flow_history_id=flow_id_version,
                        activity_history_id=activity_id_version,
                        activity_item_history_id=activity_item_id_version,
                    )
                )
            else:
                activity_item_answer_schemas.append(
                    AnswerActivityItemsSchema(
                        id=uuid.uuid4(),
                        respondent_id=self.user_id,
                        applet_id=applet_answer.applet_id,
                        answer=json.dumps(answer.answer.dict()),
                        applet_history_id=applet_id_version,
                        activity_history_id=activity_id_version,
                        activity_item_history_id=activity_item_id_version,
                    )
                )

        if activity_item_answer_schemas:
            await AnswerActivityItemsCRUD(self.session).create_many(
                activity_item_answer_schemas
            )
        elif flow_item_answer_schemas:
            await AnswerFlowItemsCRUD(self.session).create_many(
                activity_item_answer_schemas
            )
