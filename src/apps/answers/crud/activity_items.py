import json
import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Query

from apps.activities.db.schemas import ActivityItemHistorySchema
from apps.answers.db.schemas import AnswerActivityItemsSchema
from apps.answers.domain import AnsweredActivityItem, AppletAnswerCreate
from infrastructure.database.crud import BaseCRUD


class AnswerActivityItemsCRUD(BaseCRUD[AnswerActivityItemsSchema]):
    schema_class = AnswerActivityItemsSchema

    async def create_many(
        self, schemas: list[AnswerActivityItemsSchema]
    ) -> list[AnswerActivityItemsSchema]:
        for schema in schemas:
            schema.answer = json.dumps(schema.answer, default=str)
        schemas = await self._create_many(schemas)
        return schemas

    async def delete_by_applet_user(
        self, applet_id: uuid.UUID, user_id: uuid.UUID | None = None
    ):
        query: Query = delete(AnswerActivityItemsSchema)
        query = query.where(AnswerActivityItemsSchema.applet_id == applet_id)
        if user_id:
            query = query.where(
                AnswerActivityItemsSchema.respondent_id == user_id
            )
        await self._execute(query)

    async def get_for_answers_created(
        self,
        respondent_id: uuid.UUID,
        applet_answer: AppletAnswerCreate,
        activity_item_id_version,
    ) -> list[AnswerActivityItemsSchema]:

        answers = list()
        for activity_item_answer in applet_answer.answers:
            answers.append(activity_item_answer.answer)

        query: Query = select(AnswerActivityItemsSchema)
        query = query.where(
            AnswerActivityItemsSchema.applet_id == applet_answer.applet_id
        )
        query = query.where(
            AnswerActivityItemsSchema.respondent_id == respondent_id
        )
        query = query.where(
            AnswerActivityItemsSchema.activity_item_history_id
            == activity_item_id_version
        )
        query = query.where(AnswerActivityItemsSchema.answer.in_(answers))

        result = await self._execute(query)

        return result.scalars().all()

    async def get_by_answer_id(
        self, answer_id: uuid.UUID
    ) -> list[AnsweredActivityItem]:
        query: Query = select(AnswerActivityItemsSchema)
        query = query.join(
            ActivityItemHistorySchema,
            ActivityItemHistorySchema.id_version
            == AnswerActivityItemsSchema.activity_item_history_id,
        )
        query = query.where(AnswerActivityItemsSchema.answer_id == answer_id)
        query = query.order_by(ActivityItemHistorySchema.order.asc())

        db_result = await self._execute(query)
        schemas = db_result.scalars().all()
        answers = []
        for schema in schemas:  # type: AnswerActivityItemsSchema
            answers.append(
                AnsweredActivityItem(
                    activity_item_history_id=schema.activity_item_history_id,
                    answer=json.loads(schema.answer),
                )
            )

        return answers
