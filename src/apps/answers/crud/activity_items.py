import json
import typing

from sqlalchemy import delete
from sqlalchemy.orm import Query

from apps.answers.db.schemas import AnswerActivityItemsSchema
from infrastructure.database.crud import BaseCRUD


class AnswerActivityItemsCRUD(BaseCRUD[AnswerActivityItemsSchema]):
    schema_class = AnswerActivityItemsSchema

    async def create_many(
        self, schemas: list[AnswerActivityItemsSchema]
    ) -> list[AnswerActivityItemsSchema]:
        for schema in schemas:
            schema.answer = self._encrypt(schema.answer)

        schemas = await self._create_many(schemas)

        for schema in schemas:
            schema.answer = self._decrypt(schema.answer)

        return schemas

    def _encrypt(self, value: typing.Any):
        return json.dumps(value)

    def _decrypt(self, value: str):
        return json.loads(value)

    async def delete_by_applet_id(self, applet_id: int):
        raise NotImplemented
        query: Query = delete(AnswerActivityItemsSchema)
        query = query.where(AnswerActivityItemsSchema.applet_id == applet_id)
        await self._execute(query)
