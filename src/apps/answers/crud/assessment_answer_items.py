import uuid

from sqlalchemy import select
from sqlalchemy.orm import Query

from apps.answers.db.schemas import AssessmentAnswerItemSchema
from infrastructure.database.crud import BaseCRUD


class AssessmentAnswerItemsCRUD(BaseCRUD[AssessmentAnswerItemSchema]):
    schema_class = AssessmentAnswerItemSchema

    async def create_many(
        self, schemas: list[AssessmentAnswerItemSchema]
    ) -> list[AssessmentAnswerItemSchema]:
        raise NotImplementedError

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
