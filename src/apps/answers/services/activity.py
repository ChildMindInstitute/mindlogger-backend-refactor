import json
import uuid

from apps.activities.services.activity_item_history import (
    ActivityItemHistoryService,
)
from apps.answers.crud import AnswerActivityItemsCRUD
from apps.answers.db.schemas import AnswerActivityItemsSchema
from apps.answers.domain import ActivityAnswerCreate


class ActivityAnswerService:
    def __init__(self, user_id: uuid.UUID | None):
        self.user_id = user_id

    async def create_answer(self, activity_answer: ActivityAnswerCreate):
        if self.user_id:
            await self._create_respondent_answer(activity_answer)
        else:
            await self._create_anonymous_answer(activity_answer)

    async def _create_respondent_answer(
        self, activity_answer: ActivityAnswerCreate
    ):
        await self._validate_respondent_answer(activity_answer)

    async def _create_anonymous_answer(
        self, activity_answer: ActivityAnswerCreate
    ):
        await self._validate_anonymous_answer(activity_answer)

    async def _validate_respondent_answer(
        self, activity_answer: ActivityAnswerCreate
    ):
        await self._validate_answer(activity_answer)

    async def _validate_anonymous_answer(
        self, activity_answer: ActivityAnswerCreate
    ):
        await self._validate_answer(activity_answer)

    async def _validate_answer(self, activity_answer: ActivityAnswerCreate):
        activity_items = await ActivityItemHistoryService(
            activity_answer.applet_id, activity_answer.version
        ).get_by_activity_id(activity_answer.activity_id)
        

    async def _create_answer(self, activity_answer: ActivityAnswerCreate):
        applet_id_version = (
            f"{activity_answer.applet_id}_{activity_answer.version}"
        )
        activity_id_version = (
            f"{activity_answer.activity_id}_{activity_answer.version}"
        )
        schemas = []
        for answer in activity_answer.answers:
            activity_item_id_version = (
                f"{answer.activity_item_id}_{activity_answer.version}"
            )
            schemas.append(
                AnswerActivityItemsSchema(
                    respondent_id=self.user_id,
                    answer=json.dumps(answer.answer),
                    applet_history_id=applet_id_version,
                    activity_history_id=activity_id_version,
                    activity_item_history_id=activity_item_id_version,
                )
            )

        await AnswerActivityItemsCRUD().create_many(schemas)
