import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Query

from apps.answers.db.schemas import AnswerItemSchema
from apps.answers.domain import AppletAnswerCreate
from infrastructure.database.crud import BaseCRUD


class AnswerItemsCRUD(BaseCRUD[AnswerItemSchema]):
    schema_class = AnswerItemSchema

    async def create_many(
        self, schemas: list[AnswerItemSchema]
    ) -> list[AnswerItemSchema]:
        schemas = await self._create_many(schemas)
        return schemas

    async def delete_by_applet_user(
        self, applet_id: uuid.UUID, user_id: uuid.UUID | None = None
    ):
        query: Query = delete(AnswerItemSchema)
        query = query.where(AnswerItemSchema.applet_id == applet_id)
        if user_id:
            query = query.where(AnswerItemSchema.respondent_id == user_id)
        await self._execute(query)

    async def get_for_answers_created(
        self,
        respondent_id: uuid.UUID,
        applet_answer: AppletAnswerCreate,
        activity_item_id_version,
        flow_id_version: str,
    ) -> list[AnswerItemSchema]:
        answers = list()
        for activity_item_answer in applet_answer.answers:
            answers.append(activity_item_answer.answer)

        query: Query = select(AnswerItemSchema)
        query = query.where(
            AnswerItemSchema.applet_id == applet_answer.applet_id
        )
        query = query.where(AnswerItemSchema.respondent_id == respondent_id)
        query = query.where(
            AnswerItemSchema.flow_history_id == flow_id_version
        )
        query = query.where(
            AnswerItemSchema.activity_item_history_id
            == activity_item_id_version
        )
        query = query.where(AnswerItemSchema.answer.in_(answers))

        result = await self._execute(query)

        return result.scalars().all()

    async def get_by_answer_and_activity(
        self, answer_id: uuid.UUID, activity_history_id: str
    ) -> list[AnswerItemSchema]:
        query: Query = select(AnswerItemSchema)
        query = query.where(AnswerItemSchema.answer_id == answer_id)
        query = query.where(
            AnswerItemSchema.activity_history_id == activity_history_id
        )

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_answer_ids(
        self, answer_ids: list[uuid.UUID]
    ) -> list[AnswerItemSchema]:
        query: Query = select(AnswerItemSchema)
        query = query.where(AnswerItemSchema.answer_id.in_(answer_ids))
        db_result = await self._execute(query)
        return db_result.scalars().all()
