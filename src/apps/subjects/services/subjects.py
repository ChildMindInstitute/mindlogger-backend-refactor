import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.shared.exception import NotFoundError
from apps.subjects.crud import SubjectsCrud, SubjectsRespondentsCrud
from apps.subjects.db.schemas import SubjectRespondentSchema, SubjectSchema
from apps.subjects.domain import (
    Subject,
    SubjectBase,
    SubjectFull,
    SubjectRespondent,
)
from apps.users import UserSchema
from apps.users.cruds.user import UsersCRUD
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role

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

    async def _create_subject(self, schema: Subject) -> SubjectSchema:
        subj_crud = SubjectsCrud(self.session)
        subject = self.__to_db_model(schema)
        subject_entity = await subj_crud.create(subject)
        return subject_entity

    async def create(self, schema: Subject) -> SubjectSchema:
        return await self._create_subject(schema)

    async def create_many(self, schema: list[Subject]) -> list[SubjectSchema]:
        models = list(map(lambda s: self.__to_db_model(s), schema))
        return await SubjectsCrud(self.session).create_many(models)

    async def update(self, schema: SubjectSchema) -> SubjectSchema:
        return await SubjectsCrud(self.session).update(schema)

    async def delete(self, id_: uuid.UUID):
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

    async def get_full(self, subject_id: uuid.UUID):
        subject = await self.get(subject_id)
        subject_resp_crud = SubjectsRespondentsCrud(self.session)
        respondents = await subject_resp_crud.list_by_subject(subject_id)
        respondent_models = []
        for respondent, user_id in respondents:
            respondent_models.append(
                SubjectRespondent(
                    id=respondent.id,
                    respondent_access_id=respondent.respondent_access_id,
                    subject_id=respondent.subject_id,
                    relation=respondent.relation,
                    user_id=user_id,
                )
            )
        return SubjectFull(
            **SubjectBase.from_orm(subject).dict(), subjects=respondent_models
        )

    async def add_respondent(
        self,
        respondent_id: uuid.UUID,
        subject_id: uuid.UUID,
        applet_id: uuid.UUID,
        relation: str,
    ) -> SubjectFull:
        access = await UserAppletAccessCRUD(
            self.session
        ).get_applet_role_by_user_id(applet_id, respondent_id, Role.RESPONDENT)
        assert access
        subject_resp_crud = SubjectsRespondentsCrud(self.session)
        await subject_resp_crud.create(
            SubjectRespondentSchema(
                respondent_access_id=access.id,
                subject_id=subject_id,
                relation=relation,
            )
        )
        return await self.get_full(subject_id)

    async def remove_respondent(
        self, access_id: uuid.UUID, subject_id: uuid.UUID
    ):
        subject_resp_crud = SubjectsRespondentsCrud(self.session)
        await subject_resp_crud.delete_from_applet(
            subject_id=subject_id, access_id=access_id
        )
        return await self.get_full(subject_id)

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
