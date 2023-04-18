import datetime
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Query

from apps.alerts.errors import AnswerNotFoundError
from apps.answers.db.schemas import AnswerSchema
from infrastructure.database.crud import BaseCRUD


class AnswersCRUD(BaseCRUD[AnswerSchema]):
    schema_class = AnswerSchema

    async def create_many(
        self, schemas: list[AnswerSchema]
    ) -> list[AnswerSchema]:
        schemas = await self._create_many(schemas)
        return schemas

    async def get_respondents_answered_activities_by_applet_id(
        self,
        respondent_id: uuid.UUID,
        applet_id: uuid.UUID,
        created_date: datetime.date,
    ) -> list[AnswerSchema]:

        query: Query = select(AnswerSchema)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.where(AnswerSchema.respondent_id == respondent_id)
        query = query.where(func.date(AnswerSchema.created_at) == created_date)
        query = query.order_by(AnswerSchema.created_at.asc())

        db_result = await self._execute(query)
        return db_result.scalars().all()

    async def get_respondents_submit_dates(
        self,
        respondent_id: uuid.UUID,
        applet_id: uuid.UUID,
        from_date: datetime.date,
        to_date: datetime.date,
    ) -> list[datetime.date]:
        query: Query = select(func.date(AnswerSchema.created_at))
        query = query.where(AnswerSchema.respondent_id == respondent_id)
        query = query.where(func.date(AnswerSchema.created_at) >= from_date)
        query = query.where(func.date(AnswerSchema.created_at) <= to_date)
        query = query.where(AnswerSchema.applet_id == applet_id)
        query = query.order_by(AnswerSchema.created_at.asc())

        db_result = await self._execute(query)

        return db_result.scalars().all()

    async def get_by_id(self, id_: uuid.UUID) -> AnswerSchema:
        schema = await self._get("id", id_)
        if not schema:
            raise AnswerNotFoundError()
        return schema
