import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.alerts.crud.alert import AlertCRUD
from apps.shared.exception import NotFoundError
from apps.subjects.crud import SubjectsCrud
from apps.subjects.db.schemas import SubjectRelationSchema, SubjectSchema
from apps.subjects.domain import Subject
from apps.users import UserSchema
from apps.users.cruds.user import UsersCRUD

__all__ = ["SubjectsService"]


class SubjectsService:
    def __init__(self, session: AsyncSession, user_id: uuid.UUID):
        self.session = session
        self.user_id = user_id

    @staticmethod
    def __to_db_model(schema: Subject):
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
        )

    async def create(self, schema: Subject) -> Subject:
        return await SubjectsCrud(self.session).upsert(schema)

    async def create_many(self, schema: list[Subject]) -> list[SubjectSchema]:
        models = list(map(lambda s: self.__to_db_model(s), schema))
        return await SubjectsCrud(self.session).create_many(models)

    async def update(self, schema: SubjectSchema) -> SubjectSchema:
        return await SubjectsCrud(self.session).update(schema)

    async def delete(self, id_: uuid.UUID):
        repository = SubjectsCrud(self.session)
        await repository.delete_subject_relations(id_)
        return await SubjectsCrud(self.session).delete_by_id(id_)

    async def extend(self, subject_id: uuid.UUID) -> Subject | None:
        """
        Extend shell account with full account for current user
        """
        crud = SubjectsCrud(self.session)
        subject = await crud.get_by_id(subject_id)
        if subject:
            subject.user_id = self.user_id
            subject_model = await crud.update(subject)
            return Subject.from_orm(subject_model)
        return None

    async def get(self, id_: uuid.UUID) -> SubjectSchema | None:
        return await SubjectsCrud(self.session).get_by_id(id_)

    async def create_relation(
        self,
        subject_id: uuid.UUID,
        source_subject_id: uuid.UUID,
        relation: str,
    ):
        repository = SubjectsCrud(self.session)
        await repository.create_relation(
            SubjectRelationSchema(
                source_subject_id=source_subject_id,
                target_subject_id=subject_id,
                relation=relation,
            )
        )

    async def delete_relation(
        self, subject_id: uuid.UUID, source_subject_id: uuid.UUID
    ):
        repository = SubjectsCrud(self.session)
        await repository.delete_relation(subject_id, source_subject_id)

    async def create_anonymous_subject(
        self, anonymous_user: UserSchema, applet_id: uuid.UUID
    ) -> Subject:
        return await self.create(
            Subject(
                applet_id=applet_id,
                creator_id=self.user_id,
                first_name=anonymous_user.first_name,
                last_name=anonymous_user.last_name,
                secret_user_id=str(uuid.uuid4()),
            )
        )

    async def create_applet_managers(
        self, applet_id: uuid.UUID, manager_id: uuid.UUID | None
    ) -> list[SubjectSchema]:
        user_ids = [self.user_id]  # owner
        if manager_id and manager_id != self.user_id:
            user_ids.append(manager_id)
        users = await UsersCRUD(self.session).get_by_ids(user_ids)
        subjects = []
        for owner_or_manager in users:
            if owner_or_manager:
                subjects.append(
                    Subject(
                        applet_id=applet_id,
                        creator_id=self.user_id,
                        email=owner_or_manager.email_encrypted,
                        first_name=owner_or_manager.first_name,
                        last_name=owner_or_manager.last_name,
                        secret_user_id=str(uuid.uuid4()),
                        user_id=owner_or_manager.id,
                    )
                )
        return await self.create_many(subjects)

    async def exist(self, subject_id: uuid.UUID, applet_id: uuid.UUID):
        return await SubjectsCrud(self.session).exist(subject_id, applet_id)

    async def check_exist(self, subject_id: uuid.UUID, applet_id: uuid.UUID):
        is_exist = await self.exist(subject_id, applet_id)
        if not is_exist:
            raise NotFoundError()

    async def check_secret_id(
        self, subject_id: uuid.UUID, secret_id: str, applet_id: uuid.UUID
    ) -> bool:
        return await SubjectsCrud(self.session).check_secret_id(
            subject_id, secret_id, applet_id
        )

    async def upsert(self, subject: Subject) -> Subject:
        schema = await SubjectsCrud(self.session).upsert(subject)
        return Subject.from_orm(schema)

    async def get_by_user_and_applet(
        self, user_id: uuid.UUID, applet_id: uuid.UUID
    ) -> Subject | None:
        model = await SubjectsCrud(self.session).get_by_user_and_applet(
            user_id, applet_id
        )
        return Subject.from_orm(model) if model else None

    async def delete_hard(self, id_: uuid.UUID):
        await AlertCRUD(self.session).delete_by_subject(id_)

        repository = SubjectsCrud(self.session)
        await repository.delete_subject_relations(id_)
        await repository.delete(id_)
