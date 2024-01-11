import uuid

from sqlalchemy import select
from sqlalchemy.orm import Query

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

    async def is_secret_id_exist(
        self, secret_id: str, applet_id: uuid.UUID, email: str | None
    ) -> bool:
        query: Query = select(SubjectSchema.id)
        query = query.where(
            SubjectSchema.secret_user_id == secret_id,
            SubjectSchema.applet_id == applet_id,
        )
        if email:
            query = query.where(SubjectSchema.email != email)
        res = await self._execute(query)
        res = res.scalars().all()
        return bool(res)

    async def get_by_email(self, email: str) -> SubjectSchema | None:
        query: Query = select(SubjectSchema)
        query = query.where(SubjectSchema.email == email)
        query = query.limit(1)
        result = await self._execute(query)
        return result.scalars().first()
