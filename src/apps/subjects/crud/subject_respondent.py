import uuid

from apps.subjects.db.schemas import SubjectRespondentSchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["SubjectsRespondentsCrud"]


class SubjectsRespondentsCrud(BaseCRUD[SubjectRespondentSchema]):
    schema_class = SubjectRespondentSchema

    async def save(
        self, schema: SubjectRespondentSchema
    ) -> SubjectRespondentSchema:
        return await self._create(schema)

    async def get_by_id(self, pk: uuid.UUID) -> SubjectRespondentSchema | None:
        return await self._get("id", pk)

    async def update_by_id(
        self, schema: SubjectRespondentSchema
    ) -> SubjectRespondentSchema:
        return await self._update_one("id", schema.id, schema)

    async def delete(self, pk: uuid.UUID):
        return await self._delete("id", pk)
