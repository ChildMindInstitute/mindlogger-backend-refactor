import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from apps.alerts.crud.alert import AlertCRUD
from apps.invitations.constants import InvitationStatus
from apps.invitations.crud import InvitationCRUD
from apps.subjects.crud import SubjectsCrud
from apps.subjects.db.schemas import SubjectRelationSchema, SubjectSchema
from apps.subjects.domain import Subject, SubjectCreate, SubjectRelation

__all__ = ["SubjectsService"]

from apps.subjects.errors import SecretIDUniqueViolationError


class SubjectsService:
    def __init__(self, session: AsyncSession, user_id: uuid.UUID):
        self.session = session
        self.user_id = user_id

    @staticmethod
    def __to_db_model(schema: SubjectCreate):
        return SubjectSchema(
            applet_id=schema.applet_id,
            email=schema.email,
            user_id=schema.user_id,
            creator_id=schema.creator_id,
            language=schema.language,
            nickname=schema.nickname,
            first_name=schema.first_name,
            last_name=schema.last_name,
            secret_user_id=schema.secret_user_id,
            tag=schema.tag,
        )

    async def create(self, schema: SubjectCreate) -> Subject:
        subject_with_secret = await self.get_by_secret_id(schema.applet_id, schema.secret_user_id)
        if subject_with_secret and not subject_with_secret.is_deleted:
            raise SecretIDUniqueViolationError()

        updated_schema = await SubjectsCrud(self.session).upsert(schema)
        return Subject.from_orm(updated_schema)

    async def update(self, id_: uuid.UUID, **values) -> SubjectSchema:
        return await SubjectsCrud(self.session).update_by_id(id_, **values)

    async def delete(self, id_: uuid.UUID):
        await InvitationCRUD(self.session).delete_by_subject(id_, [InvitationStatus.PENDING])
        repository = SubjectsCrud(self.session)
        await repository.delete_subject_relations(id_)
        return await repository.delete_by_id(id_)

    async def extend(self, subject_id: uuid.UUID, email: str) -> Subject | None:
        """
        Extend shell account with full account for current user
        """
        crud = SubjectsCrud(self.session)
        subject = await crud.get_by_id(subject_id)
        if subject:
            subject.user_id = self.user_id
            subject.email = email
            subject_model = await crud.update(subject)
            return Subject.from_orm(subject_model)
        return None

    async def get(self, id_: uuid.UUID) -> Subject | None:
        schema = await SubjectsCrud(self.session).get_by_id(id_)
        return Subject.from_orm(schema) if schema else None

    async def get_by_ids(self, ids: list[uuid.UUID], include_deleted=False) -> list[Subject]:
        subjects = await SubjectsCrud(self.session).get_by_ids(ids, include_deleted)
        return [Subject.from_orm(subject) for subject in subjects]

    async def get_if_soft_exist(self, id_: uuid.UUID) -> Subject | None:
        schema = await SubjectsCrud(self.session).get_by_id(id_)
        if schema and schema.soft_exists():
            return Subject.from_orm(schema)
        return None

    async def create_relation(
        self, subject_id: uuid.UUID, source_subject_id: uuid.UUID, relation: str, meta: dict[str, Any] = {}
    ):
        repository = SubjectsCrud(self.session)
        await repository.create_relation(
            SubjectRelationSchema(
                source_subject_id=source_subject_id,
                target_subject_id=subject_id,
                relation=relation,
                meta=meta,
            )
        )

    async def delete_relation(self, subject_id: uuid.UUID, source_subject_id: uuid.UUID):
        repository = SubjectsCrud(self.session)
        await repository.delete_relation(subject_id, source_subject_id)

    async def get_relation(self, source_subject_id: uuid.UUID, target_subject_id: uuid.UUID) -> SubjectRelation | None:
        return await SubjectsCrud(self.session).get_relation(source_subject_id, target_subject_id)

    async def get_by_secret_id(self, applet_id: uuid.UUID, secret_id: str) -> Subject | None:
        subject = await SubjectsCrud(self.session).get_by_secret_id(applet_id, secret_id)
        if subject:
            return Subject.from_orm(subject)
        return None

    async def check_secret_id(self, subject_id: uuid.UUID, secret_id: str, applet_id: uuid.UUID) -> bool:
        subject = await self.get_by_secret_id(applet_id, secret_id)
        if subject and subject.id != subject_id:
            return True
        return False

    async def upsert(self, subject: Subject) -> Subject:
        schema = await SubjectsCrud(self.session).upsert(subject)
        return Subject.from_orm(schema)

    async def get_by_user_and_applet(self, user_id: uuid.UUID, applet_id: uuid.UUID) -> Subject | None:
        model = await SubjectsCrud(self.session).get_by_user_and_applet(user_id, applet_id)
        return Subject.from_orm(model) if model else None

    async def delete_hard(self, id_: uuid.UUID):
        await InvitationCRUD(self.session).delete_by_subject(id_)
        await AlertCRUD(self.session).delete_by_subject(id_)
        repository = SubjectsCrud(self.session)
        await repository.delete_subject_relations(id_)
        await repository.delete(id_)

    async def get_pending_subject_if_exist(self, secret_id: str, applet_id: uuid.UUID) -> SubjectCreate | None:
        models = await SubjectsCrud(self.session).get_pending_subjects(secret_id, applet_id)
        return models[0] if models else None
