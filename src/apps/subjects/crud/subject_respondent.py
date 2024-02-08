import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Query

from apps.subjects.db.schemas import SubjectRespondentSchema
from apps.workspaces.db.schemas.user_applet_access import UserAppletAccessSchema
from infrastructure.database.crud import BaseCRUD

__all__ = ["SubjectsRespondentsCrud"]


class SubjectsRespondentsCrud(BaseCRUD[SubjectRespondentSchema]):
    schema_class = SubjectRespondentSchema

    async def create(
        self, schema: SubjectRespondentSchema
    ) -> SubjectRespondentSchema:
        return await self._create(schema)

    async def get_by_id(self, pk: uuid.UUID) -> SubjectRespondentSchema | None:
        return await self._get("id", pk)

    async def update_by_id(
        self, schema: SubjectRespondentSchema
    ) -> SubjectRespondentSchema:
        return await self._update_one("id", schema.id, schema)

    async def delete(self, id_: uuid.UUID):
        return await self._delete(id=id_)

    async def list_by_subject(
        self, subject_id: uuid.UUID
    ) -> list[tuple[SubjectRespondentSchema, uuid.UUID]]:
        query: Query = select(
            SubjectRespondentSchema, UserAppletAccessSchema.user_id
        )
        query = query.where(SubjectRespondentSchema.subject_id == subject_id)
        query = query.join(
            UserAppletAccessSchema,
            UserAppletAccessSchema.id
            == SubjectRespondentSchema.respondent_access_id,
            isouter=True,
        )
        result = await self._execute(query)
        return result.all()

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
