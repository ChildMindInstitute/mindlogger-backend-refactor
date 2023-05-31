import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Query

from apps.answers.db.schemas import AssessmentAnswerItemSchema
from infrastructure.database.crud import BaseCRUD


class AssessmentAnswerItemsCRUD(BaseCRUD[AssessmentAnswerItemSchema]):
    schema_class = AssessmentAnswerItemSchema

    async def create(
        self, schema: AssessmentAnswerItemSchema
    ) -> AssessmentAnswerItemSchema:
        delete_query: Query = delete(AssessmentAnswerItemSchema)
        delete_query = delete_query.where(
            AssessmentAnswerItemSchema.answer_id == schema.answer_id
        )
        delete_query = delete_query.where(
            AssessmentAnswerItemSchema.reviewer_id == schema.reviewer_id
        )
        delete_query = delete_query.returning(AssessmentAnswerItemSchema.id)
        db_result = await self._execute(delete_query)
        schema.is_edited = db_result.scalars().first() is not None

        return await self._create(schema)

    async def get_by_answer_and_activity(
        self,
        answer_id: uuid.UUID,
        activity_history_id: str,
        reviewer_id: uuid.UUID,
    ) -> AssessmentAnswerItemSchema | None:
        query: Query = select(AssessmentAnswerItemSchema)
        query = query.where(AssessmentAnswerItemSchema.answer_id == answer_id)
        query = query.where(
            AssessmentAnswerItemSchema.reviewer_id == reviewer_id
        )
        query = query.where(
            AssessmentAnswerItemSchema.activity_history_id
            == activity_history_id
        )

        db_result = await self._execute(query)
        return db_result.scalars().first()
