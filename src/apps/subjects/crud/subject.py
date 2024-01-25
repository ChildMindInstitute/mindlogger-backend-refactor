import uuid

from sqlalchemy import and_, select
from sqlalchemy.orm import Query

from apps.subjects.db.schemas import SubjectRespondentSchema, SubjectSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.database.crud import BaseCRUD

__all__ = ["SubjectsCrud"]


class SubjectsCrud(BaseCRUD[SubjectSchema]):
    schema_class = SubjectSchema

    async def create(self, schema: SubjectSchema) -> SubjectSchema:
        return await self._create(schema)

    async def create_many(
        self, schema: list[SubjectSchema]
    ) -> list[SubjectSchema]:
        return await self._create_many(schema)

    async def get_by_id(self, _id: uuid.UUID) -> SubjectSchema | None:
        return await self._get("id", _id)

    async def get_by_user(self, user_id: uuid.UUID) -> SubjectSchema | None:
        return await self._get("user_id", user_id)

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

    async def get_source(
        self, user_id: uuid.UUID, target_id: uuid.UUID, applet_id: uuid.UUID
    ) -> SubjectSchema | None:
        """
        Function to get source subject
        Parameters
        ----------
        user_id: uuid.UUID
            Source user_id
        target_id: uuid.UUID
            Target subject id
        applet_id: uuid.UUID
            Applet id
        """
        query: Query = select(SubjectSchema)
        query = query.join(
            SubjectRespondentSchema,
            SubjectRespondentSchema.subject_id == SubjectSchema.id,
        )
        query = query.join(
            UserAppletAccessSchema,
            (
                UserAppletAccessSchema.id
                == SubjectRespondentSchema.respondent_access_id
            ),
        )
        query = query.where(
            SubjectRespondentSchema.subject_id == target_id,
            UserAppletAccessSchema.applet_id == applet_id,
            UserAppletAccessSchema.user_id == user_id,
        )
        query = query.limit(1)
        res = await self._execute(query)
        return res.scalar_one_or_none()

    async def get_self_subject(
        self, user_id: uuid.UUID, applet_id: uuid.UUID
    ) -> SubjectSchema | None:
        query: Query = select(SubjectSchema)
        query = query.where(
            SubjectSchema.user_id == user_id,
            SubjectSchema.applet_id == applet_id,
        )
        query = query.limit(1)
        res = await self._execute(query)
        return res.scalar_one_or_none()

    async def get_relation(
        self,
        target_id: uuid.UUID,
        source_user_id: uuid.UUID,
        applet_id: uuid.UUID,
    ) -> str | None:
        query: Query = select(SubjectRespondentSchema.relation)
        query = query.join(
            UserAppletAccessSchema,
            and_(
                UserAppletAccessSchema.id
                == SubjectRespondentSchema.respondent_access_id,
                UserAppletAccessSchema.user_id == source_user_id,
                UserAppletAccessSchema.applet_id == applet_id,
                UserAppletAccessSchema.role == Role.RESPONDENT,
            ),
            isouter=True,
        )
        query = query.where(SubjectRespondentSchema.subject_id == target_id)
        result = await self._execute(query)
        return result.scalar_one_or_none()

    async def exist(self, subject_id: uuid.UUID, applet_id: uuid.UUID) -> bool:
        query: Query = select(SubjectSchema.id)
        query = query.where(
            SubjectSchema.id == subject_id,
            SubjectSchema.applet_id == applet_id,
        )
        res = await self._execute(query)
        return bool(res.scalar_one_or_none())

    async def update(self, schema: SubjectSchema) -> SubjectSchema:
        return await self._update_one("id", schema.id, schema)

    async def check_secret_id(
        self, subject_id: uuid.UUID, secret_id: str, applet_id: uuid.UUID
    ) -> bool:
        query: Query = select(SubjectSchema.id)
        query = query.where(
            SubjectSchema.secret_user_id == secret_id,
            SubjectSchema.applet_id == applet_id,
            SubjectSchema.id != subject_id,
        )
        query = query.limit(1)
        res = await self._execute(query)
        return bool(res.scalar_one_or_none())
