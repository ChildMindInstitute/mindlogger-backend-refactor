import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Query

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

    async def list_by_subject(
        self, subject_id: uuid.UUID
    ) -> list[SubjectRespondentSchema]:
        query: Query = select(SubjectRespondentSchema)
        query = query.where(SubjectRespondentSchema.subject_id == subject_id)
        result = await self._execute(query)
        return result.scalars().all()

    async def delete_from_applet(
        self,
        subject_id: uuid.UUID,
        access_id: uuid.UUID,
    ):
        query: Query = delete(SubjectRespondentSchema)
        query = query.where(
            SubjectRespondentSchema.subject_id == subject_id,
            SubjectRespondentSchema.respondent_access_id == access_id,
        )
        await self._execute(query)
