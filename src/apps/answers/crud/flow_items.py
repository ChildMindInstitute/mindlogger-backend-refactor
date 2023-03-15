import typing
import uuid

from sqlalchemy import delete
from sqlalchemy.orm import Query

from apps.answers.db.schemas import AnswerFlowItemsSchema
from infrastructure.database.crud import BaseCRUD


class AnswerFlowItemsCRUD(BaseCRUD[AnswerFlowItemsSchema]):
    schema_class = AnswerFlowItemsSchema

    async def create_many(
        self, schemas: list[AnswerFlowItemsSchema]
    ) -> list[AnswerFlowItemsSchema]:
        for schema in schemas:
            schema.answer = self._encrypt(schema.answer)

        schemas = await self._create_many(schemas)

        for schema in schemas:
            schema.answer = self._decrypt(schema.answer)

        return schemas

    def _encrypt(self, value: typing.Any):
        return value

    def _decrypt(self, value: str):
        return value

    async def delete_by_applet_id(self, applet_id: uuid.UUID):
        query: Query = delete(AnswerFlowItemsSchema)
        query = query.where(AnswerFlowItemsSchema.applet_id == applet_id)
        await self._execute(query)
