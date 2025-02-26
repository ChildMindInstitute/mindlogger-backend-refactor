import hashlib
import uuid

from apps.applets.crud.applets import AppletsCRUD
from apps.authentication.services.security import AuthenticationService
from apps.integrations.domain import AvailableIntegrations
from apps.integrations.prolific.domain import ProlificUserInfo
from apps.integrations.prolific.errors import ProlificInvalidStudyError
from apps.shared.hashing import hash_sha224
from apps.subjects.domain import SubjectCreate
from apps.subjects.services.subjects import SubjectsService
from apps.users.cruds.user import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.users.domain import ProlificPublicUser
from config import settings


class ProlificUserService:
    def __init__(self, session, prolific_participant: ProlificUserInfo) -> None:
        self.session = session
        self.prolific_pid = prolific_participant.prolific_pid
        self.prolific_study_id = prolific_participant.study_id

    async def user_exists(self) -> ProlificPublicUser:
        prolific_respondent_id = self._get_id_by_prolific_params()
        crud = UsersCRUD(self.session)

        prolific_respondent = await crud.get_prolific_respondent(prolific_respondent_id)

        return ProlificPublicUser(exists=prolific_respondent is not None)

    async def create_prolific_respondent(self, applet_id: uuid.UUID):
        prolific_respondent = await self.create_prolific_user()
        await self.create_subject(prolific_respondent, applet_id)

        return prolific_respondent

    async def create_prolific_user(self) -> UserSchema:
        prolific_respondent_id = self._get_id_by_prolific_params()

        crud = UsersCRUD(self.session)

        prolific_respondent = await crud.get_prolific_respondent(prolific_respondent_id)
        if not prolific_respondent:
            prolific_respondent = UserSchema(
                id=prolific_respondent_id,
                email=hash_sha224(self._get_formated_email()),
                first_name=settings.prolific_respondent.first_name,
                last_name=settings.prolific_respondent.last_name,
                hashed_password=AuthenticationService(self.session).get_password_hash(
                    settings.prolific_respondent.password
                ),
                email_encrypted=self._get_formated_email(),
            )

            return await crud.save(prolific_respondent)

        # As the id is generated from the prolific_pid and prolific_study_id
        # that means the user already answered this survey.
        raise ProlificInvalidStudyError(message="User already answered the survey")

    async def create_subject(self, prolific_respondent: UserSchema, applet_id: uuid.UUID) -> None:
        subject_service = SubjectsService(self.session, prolific_respondent.id)
        subject = await subject_service.get_by_user_and_applet(prolific_respondent.id, applet_id)
        applet = await AppletsCRUD(session=self.session).get_by_id(applet_id)

        if not subject or subject.is_deleted:
            await subject_service.create(
                SubjectCreate(
                    applet_id=applet_id,
                    creator_id=applet.creator_id,
                    user_id=prolific_respondent.id,
                    first_name=prolific_respondent.first_name,
                    last_name=prolific_respondent.last_name,
                    secret_user_id=self._get_formated_secret_user_id(),
                    email=self._get_formated_email(),
                    integration_source=AvailableIntegrations.PROLIFIC,
                )
            )

    def _get_id_by_prolific_params(self) -> uuid.UUID:
        hash_object = hashlib.sha256(f"{self.prolific_pid}-{self.prolific_study_id}".encode("utf-8"))
        return uuid.UUID(hash_object.hexdigest()[:32])

    def _get_formated_email(self):
        return f"{self.prolific_pid}-{self.prolific_study_id}@{settings.prolific_respondent.domain}"

    def _get_formated_secret_user_id(self):
        base_secret_user_id = settings.prolific_respondent.secret_user_id
        return f"{base_secret_user_id}{self.prolific_pid}-{self.prolific_study_id}"
