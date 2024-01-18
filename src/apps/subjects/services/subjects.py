import uuid

from sqlalchemy.ext.asyncio import AsyncSession

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
from apps.users.services.user import UserService
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role

__all__ = ["SubjectsService"]


class SubjectsService:
    def __init__(
        self, session: AsyncSession, user_id: uuid.UUID, applet_id: uuid.UUID
    ):
        self.session = session
        self.user_id = user_id
        self.applet_id = applet_id

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

    async def _create_subject(self, schema: Subject) -> Subject:
        subj_crud = SubjectsCrud(self.session)
        subject = self.__to_db_model(schema)
        subject_entity = await subj_crud.create(subject)
        return Subject.from_orm(subject_entity)

    async def create(self, schema: Subject) -> Subject:
        subject = await self._create_subject(schema)
        merged_data = subject.dict()
        return Subject(**merged_data)

    async def create_many(self, schema: list[Subject]) -> list[SubjectSchema]:
        models = list(map(lambda s: self.__to_db_model(s), schema))
        return await SubjectsCrud(self.session).create_many(models)

    async def merge(self, subject_id: uuid.UUID) -> Subject | None:
        """
        Merge shell account with full account for current user
        """
        user = await UserService(self.session).get(self.user_id)
        assert user
        crud = SubjectsCrud(self.session)
        subject = await crud.get_by_id(subject_id)
        if subject:
            subject.user_id = user.id
            subject.email = user.email_encrypted
            subject.last_name = user.first_name
            subject.first_name = user.first_name
            await crud.update_by_id(subject)
            return Subject.from_orm(subject)
        return None

    async def get_by_email(self, email: str) -> Subject | None:
        return await SubjectsCrud(self.session).get_by_email(email)

    async def get(self, id_: uuid.UUID) -> Subject | None:
        return await SubjectsCrud(self.session).get_by_id(id_)

    async def get_full(self, subject_id: uuid.UUID):
        subject = await self.get(subject_id)
        subject_resp_crud = SubjectsRespondentsCrud(self.session)
        respondents = await subject_resp_crud.list_by_subject(subject_id)
        respondent_models = [
            SubjectRespondent.from_orm(respondent)
            for respondent in respondents
        ]
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
        await subject_resp_crud.save(
            SubjectRespondentSchema(
                respondent_access_id=access.id,
                subject_id=subject_id,
                relation=relation,
            )
        )
        return await self.get_full(subject_id)

    async def remove_respondent(
        self,
        respondent_id: uuid.UUID,
        subject_id: uuid.UUID,
        applet_id: uuid.UUID,
    ):
        access = await UserAppletAccessCRUD(
            self.session
        ).get_applet_role_by_user_id(applet_id, respondent_id, Role.RESPONDENT)
        assert access
        subject_resp_crud = SubjectsRespondentsCrud(self.session)
        await subject_resp_crud.delete_from_applet(
            subject_id=subject_id, access_id=access.id
        )
        return await self.get_full(subject_id)

    async def create_anonymous_subject(
        self,
        anonymous_user: UserSchema,
        applet_id: uuid.UUID,
        secret_user_id: str,
    ) -> Subject:
        return await self.create(
            Subject(
                applet_id=applet_id,
                creator_id=self.user_id,
                first_name=anonymous_user.first_name,
                last_name=anonymous_user.last_name,
                secret_user_id=secret_user_id,
            )
        )

    async def create_applet_managers(
        self, manager_id: uuid.UUID | None
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
                        applet_id=self.applet_id,
                        creator_id=self.user_id,
                        email=owner_or_manager.email_encrypted,
                        first_name=owner_or_manager.first_name,
                        last_name=owner_or_manager.last_name,
                        secret_user_id=str(uuid.uuid4()),
                        user_id=owner_or_manager.id,
                    )
                )
        return await self.create_many(subjects)
