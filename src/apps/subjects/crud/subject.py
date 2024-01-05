import uuid

from apps.subjects.db.schemas import SubjectSchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["SubjectsCrud"]


class SubjectsCrud(BaseCRUD[SubjectSchema]):
    schema_class = SubjectSchema

    async def save(self, schema: SubjectSchema) -> SubjectSchema:
        return await self._create(schema)

    async def get_by_id(self, pk: uuid.UUID) -> SubjectSchema | None:
        return await self._get("id", pk)

    async def update_by_id(self, schema: SubjectSchema) -> SubjectSchema:
        return await self._update_one("id", schema.id, schema)

    async def delete(self, pk: uuid.UUID):
        return await self._delete("id", pk)
