import uuid
from datetime import datetime

from asyncpg import UniqueViolationError
from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.dialects.postgresql import UUID, insert
from sqlalchemy.orm import Query

from apps.invitations.constants import InvitationStatus
from apps.invitations.db import InvitationSchema
from apps.subjects.db.schemas import SubjectRelationSchema, SubjectSchema
from apps.subjects.domain import Subject
from infrastructure.database.crud import BaseCRUD

__all__ = ["SubjectsCrud"]


class SubjectsCrud(BaseCRUD[SubjectSchema]):
    schema_class = SubjectSchema

    async def create(self, schema: SubjectSchema) -> SubjectSchema:
        return await self._create(schema)

    async def create_many(self, schema: list[SubjectSchema]) -> list[SubjectSchema]:
        return await self._create_many(schema)

    async def update(self, schema: SubjectSchema) -> SubjectSchema:
        return await self._update_one("id", schema.id, schema)

    async def get_by_id(self, _id: uuid.UUID) -> SubjectSchema | None:
        return await self._get("id", _id)

    async def get_by_user_and_applet(
        self,
        user_id: uuid.UUID,
        applet_id: uuid.UUID,
    ) -> SubjectSchema | None:
        query: Query = select(SubjectSchema)
        query = query.where(
            SubjectSchema.user_id == user_id,
            SubjectSchema.applet_id == applet_id,
        )
        res_db = await self._execute(query)
        return res_db.scalar_one_or_none()

    async def update_by_id(self, schema: SubjectSchema) -> SubjectSchema:
        return await self._update_one("id", schema.id, schema)

    async def delete(self, id_: uuid.UUID):
        return await self._delete(id=id_)

    async def get_by_secret_id(self, secret_id: str, applet_id: uuid.UUID) -> SubjectSchema | None:
        query: Query = select(SubjectSchema)
        query = query.where(
            SubjectSchema.secret_user_id == secret_id,
            SubjectSchema.applet_id == applet_id,
        )
        res = await self._execute(query)
        return res.scalars().first()

    async def get_pending_subjects(self, secret_id: str, applet_id: uuid.UUID, subject_id: uuid.UUID | None = None):
        query: Query = select(SubjectSchema)
        query = query.join(
            InvitationSchema,
            and_(
                InvitationSchema.meta.has_key("subject_id"),
                SubjectSchema.id == func.cast(InvitationSchema.meta["subject_id"].astext, UUID(as_uuid=True)),
                InvitationSchema.status == InvitationStatus.PENDING,
            ),
        )
        query = query.where(SubjectSchema.secret_user_id == secret_id, SubjectSchema.applet_id == applet_id)
        if subject_id:
            query = query.where(SubjectSchema.id == subject_id)
        res = await self._execute(query)
        res = res.scalars().all()
        return res

    async def get_user_subject(self, user_id: uuid.UUID, applet_id: uuid.UUID) -> SubjectSchema | None:
        query: Query = select(SubjectSchema)
        query = query.where(
            SubjectSchema.user_id == user_id,
            SubjectSchema.applet_id == applet_id,
            SubjectSchema.soft_exists(),
        )
        res = await self._execute(query)
        return res.scalar_one_or_none()

    async def get_relation(
        self,
        source_subject_id: uuid.UUID,
        target_subject_id: uuid.UUID,
    ) -> str | None:
        query: Query = select(SubjectRelationSchema.relation)
        query = query.where(
            SubjectRelationSchema.source_subject_id == source_subject_id,
            SubjectRelationSchema.target_subject_id == target_subject_id,
        )
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

    async def delete_by_id(self, id_: uuid.UUID):
        await self._update_one(lookup="id", value=id_, schema=SubjectSchema(is_deleted=True))

    async def get(self, user_id: uuid.UUID, applet_id: uuid.UUID) -> SubjectSchema | None:
        query: Query = select(SubjectSchema)
        query = query.where(
            SubjectSchema.user_id == user_id,
            SubjectSchema.applet_id == applet_id,
        )
        result = await self._execute(query)
        return result.scalar_one_or_none()

    async def check_secret_id(self, subject_id: uuid.UUID, secret_id: str, applet_id: uuid.UUID) -> bool:
        query: Query = select(SubjectSchema.id)
        query = query.where(
            SubjectSchema.secret_user_id == secret_id,
            SubjectSchema.applet_id == applet_id,
            SubjectSchema.id != subject_id,
        )
        query = query.limit(1)
        res = await self._execute(query)
        return bool(res.scalar_one_or_none())

    async def upsert(self, schema: Subject) -> Subject:
        values = {**schema.dict()}
        values.pop("id")
        stmt = insert(SubjectSchema).values(values)
        stmt = stmt.on_conflict_do_update(
            index_elements=[SubjectSchema.user_id, SubjectSchema.applet_id],
            set_={
                **values,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            where=SubjectSchema.soft_exists(exists=False),
        ).returning(SubjectSchema.id)
        result = await self._execute(stmt)
        model_id = result.scalar_one_or_none()
        if not model_id:
            raise UniqueViolationError()
        schema.id = model_id
        return schema

    async def reduce_applet_subject_ids(self, applet_id, subject_ids: list[uuid.UUID] | list[str]) -> list[uuid.UUID]:
        query = select(SubjectSchema.id).where(
            SubjectSchema.id.in_(subject_ids),
            SubjectSchema.applet_id == applet_id,
            SubjectSchema.soft_exists(),
        )
        res = await self._execute(query)

        return res.scalars().all()

    async def delete_relation(
        self,
        subject_id: uuid.UUID,
        source_subject_id: uuid.UUID,
    ):
        query: Query = delete(SubjectRelationSchema)
        query = query.where(
            SubjectRelationSchema.source_subject_id == source_subject_id,
            SubjectRelationSchema.target_subject_id == subject_id,
        )
        await self._execute(query)

    async def create_relation(self, schema: SubjectRelationSchema) -> SubjectRelationSchema:
        return await self._create(schema)

    async def delete_subject_relations(self, subject_id):
        query = delete(SubjectRelationSchema).where(
            or_(
                SubjectRelationSchema.source_subject_id == subject_id,
                SubjectRelationSchema.target_subject_id == subject_id,
            )
        )
        await self._execute(query)
