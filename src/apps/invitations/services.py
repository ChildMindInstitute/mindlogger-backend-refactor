import asyncio
import uuid

from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ErrorWrapper

from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.db.schemas import AppletSchema
from apps.applets.domain import ManagersRole, Role
from apps.applets.service import UserAppletAccessService
from apps.applets.service.applet import PublicAppletService
from apps.invitations.constants import InvitationStatus
from apps.invitations.crud import InvitationCRUD
from apps.invitations.db import InvitationSchema
from apps.invitations.domain import (
    InvitationDetail,
    InvitationDetailForManagers,
    InvitationDetailForRespondent,
    InvitationDetailForReviewer,
    InvitationDetailGeneric,
    InvitationManagers,
    InvitationManagersRequest,
    InvitationRespondent,
    InvitationRespondentRequest,
    InvitationReviewer,
    InvitationReviewerRequest,
    PrivateInvitationDetail,
    RespondentMeta,
    ReviewerMeta,
)
from apps.invitations.errors import (
    DoesNotHaveAccess,
    InvitationAlreadyProcessed,
    InvitationDoesNotExist,
    NonUniqueValue,
    RespondentDoesNotExist,
)
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.shared.query_params import QueryParams
from apps.subjects.crud import SubjectsCrud
from apps.users import UsersCRUD
from apps.users.domain import User
from apps.workspaces.service.workspace import WorkspaceService
from config import settings


class InvitationsService:
    def __init__(self, session, user: User):
        self._user: User = user
        self.invitations_crud = InvitationCRUD(session)
        self.session = session

    async def fetch_all(
        self, query_params: QueryParams
    ) -> list[InvitationDetail]:
        return await self.invitations_crud.get_pending_by_invitor_id(
            self._user.id, query_params
        )

    async def fetch_all_count(self, query_params: QueryParams) -> int:
        return await self.invitations_crud.get_pending_by_invitor_id_count(
            self._user.id, query_params
        )

    async def get(self, key: uuid.UUID) -> InvitationDetailGeneric | None:
        invitation = await self.invitations_crud.get_by_email_and_key(
            self._user.email_encrypted, key  # type: ignore[arg-type]
        )
        if not invitation:
            raise InvitationDoesNotExist()
        elif invitation.status != InvitationStatus.PENDING:
            raise InvitationAlreadyProcessed()
        return invitation

    def _get_invitation_subject(self, applet: AppletSchema):
        return f"{applet.display_name} invitation"

    async def send_respondent_invitation(
        self,
        applet_id: uuid.UUID,
        schema: InvitationRespondentRequest,
        subject_id: uuid.UUID | None,
    ) -> InvitationDetailForRespondent:
        await self._is_validated_role_for_invitation(
            applet_id, Role.RESPONDENT
        )

        # Get invited user if he exists. User will be linked with invitaion
        # by user_id in this case
        invited_user = await UsersCRUD(self.session).get_user_or_none_by_email(
            email=schema.email
        )
        invited_user_id = invited_user.id if invited_user is not None else None
        meta = RespondentMeta(subject_id=str(subject_id))
        payload = {
            "email": schema.email,
            "applet_id": applet_id,
            "role": Role.RESPONDENT,
            "key": uuid.uuid3(uuid.uuid4(), schema.email),
            "invitor_id": self._user.id,
            "status": InvitationStatus.PENDING,
            "first_name": schema.first_name,
            "last_name": schema.last_name,
            "user_id": invited_user_id,
            "meta": meta.dict(),
            "nickname": schema.nickname,
        }
        pending_invitation = await (
            self.invitations_crud.get_pending_invitation(
                schema.email, applet_id
            )
        )
        if pending_invitation:
            invitation_schema = await self.invitations_crud.update(
                lookup="id",
                value=pending_invitation.id,
                schema=InvitationSchema(**payload),
            )
        else:
            invitation_schema = await self.invitations_crud.save(
                InvitationSchema(**payload)
            )
        invitation_internal: InvitationRespondent = (
            InvitationRespondent.from_orm(invitation_schema)
        )

        applet = await AppletsCRUD(self.session).get_by_id(
            invitation_internal.applet_id
        )
        template_name = self._get_email_template_name(
            invited_user_id, schema.language
        )

        # Send email to the user
        service = MailingService()
        message = MessageSchema(
            recipients=[schema.email],
            subject=self._get_invitation_subject(applet),
            body=service.get_template(
                path=template_name,
                first_name=schema.first_name,
                last_name=schema.last_name,
                applet_name=applet.display_name,
                role=invitation_internal.role,
                link=self._get_invitation_url_by_role(
                    invitation_internal.role
                ),
                key=invitation_internal.key,
                language=schema.language,
            ),
        )
        await service.send(message)

        return InvitationDetailForRespondent(
            id=invitation_internal.id,
            secret_user_id=schema.secret_user_id,
            nickname=schema.nickname,
            applet_id=applet.id,
            applet_name=applet.display_name,
            role=invitation_internal.role,
            status=invitation_internal.status,
            key=invitation_internal.key,
            user_id=invitation_internal.user_id,
        )

    async def send_reviewer_invitation(
        self, applet_id: uuid.UUID, schema: InvitationReviewerRequest
    ) -> InvitationDetailForReviewer:
        await self._is_validated_role_for_invitation(applet_id, Role.REVIEWER)
        await self._do_respondents_exist(applet_id, schema.respondents)

        respondents = [
            str(respondent_id) for respondent_id in schema.respondents
        ]
        # Get invited user if he exists. User will be linked with invitaion
        # by user_id in this case
        invited_user = await UsersCRUD(self.session).get_user_or_none_by_email(
            email=schema.email
        )
        invited_user_id = invited_user.id if invited_user is not None else None
        payload = {
            "email": schema.email,
            "applet_id": applet_id,
            "role": Role.REVIEWER,
            "key": uuid.uuid3(uuid.uuid4(), schema.email),
            "invitor_id": self._user.id,
            "status": InvitationStatus.PENDING,
            "first_name": schema.first_name,
            "last_name": schema.last_name,
            "user_id": invited_user_id,
            "nickname": None,
            "meta": ReviewerMeta(respondents=respondents).dict(),
        }

        pending_invitation = await (
            self.invitations_crud.get_pending_invitation(
                schema.email, applet_id
            )
        )
        if pending_invitation:
            invitation_schema = await self.invitations_crud.update(
                lookup="id",
                value=pending_invitation.id,
                schema=InvitationSchema(**payload),
            )
        else:
            invitation_schema = await self.invitations_crud.save(
                InvitationSchema(**payload)
            )
        invitation_internal = InvitationReviewer.from_orm(invitation_schema)

        applet = await AppletsCRUD(self.session).get_by_id(
            invitation_internal.applet_id
        )

        template_name = self._get_email_template_name(
            invited_user_id, schema.language
        )

        await WorkspaceService(
            self.session, self._user.id
        ).update_workspace_name(self._user, schema.workspace_prefix)

        # Send email to the user
        service = MailingService()
        message = MessageSchema(
            recipients=[schema.email],
            subject=self._get_invitation_subject(applet),
            body=service.get_template(
                path=template_name,
                first_name=schema.first_name,
                last_name=schema.last_name,
                applet_name=applet.display_name,
                role=invitation_internal.role,
                link=self._get_invitation_url_by_role(
                    invitation_internal.role
                ),
                key=invitation_internal.key,
                language=schema.language,
            ),
        )

        await service.send(message)

        return InvitationDetailForReviewer(
            id=invitation_internal.id,
            email=invitation_internal.email,
            applet_id=applet.id,
            applet_name=applet.display_name,
            role=invitation_internal.role,
            status=invitation_internal.status,
            key=invitation_internal.key,
            respondents=schema.respondents,
            user_id=invitation_internal.user_id,
        )

    async def send_managers_invitation(
        self,
        applet_id: uuid.UUID,
        schema: InvitationManagersRequest,
    ) -> InvitationDetailForManagers:
        await self._is_validated_role_for_invitation(applet_id, schema.role)
        # Get invited user if he exists. User will be linked with invitaion
        # by user_id in this case
        invited_user = await UsersCRUD(self.session).get_user_or_none_by_email(
            email=schema.email
        )
        invited_user_id = invited_user.id if invited_user is not None else None
        payload = {
            "email": schema.email,
            "applet_id": applet_id,
            "role": schema.role,
            "key": uuid.uuid3(uuid.uuid4(), schema.email),
            "invitor_id": self._user.id,
            "status": InvitationStatus.PENDING,
            "first_name": schema.first_name,
            "last_name": schema.last_name,
            "user_id": invited_user_id,
            "meta": {},
        }

        pending_invitation = await (
            self.invitations_crud.get_pending_invitation(
                schema.email, applet_id
            )
        )
        if pending_invitation:
            invitation_schema = await self.invitations_crud.update(
                lookup="id",
                value=pending_invitation.id,
                schema=InvitationSchema(**payload),
            )
        else:
            invitation_schema = await self.invitations_crud.save(
                InvitationSchema(**payload)
            )
        invitation_internal = InvitationManagers.from_orm(invitation_schema)
        applet = await AppletsCRUD(self.session).get_by_id(
            invitation_internal.applet_id
        )
        template_name = self._get_email_template_name(
            invited_user_id, schema.language
        )
        await WorkspaceService(
            self.session, self._user.id
        ).update_workspace_name(self._user, schema.workspace_prefix)

        # Send email to the user
        service = MailingService()
        message = MessageSchema(
            recipients=[schema.email],
            subject=self._get_invitation_subject(applet),
            body=service.get_template(
                path=template_name,
                first_name=schema.first_name,
                last_name=schema.last_name,
                applet_name=applet.display_name,
                role=invitation_internal.role,
                link=self._get_invitation_url_by_role(
                    invitation_internal.role
                ),
                key=invitation_internal.key,
                language=schema.language,
            ),
        )

        await service.send(message)

        return InvitationDetailForManagers(
            id=invitation_internal.id,
            email=invitation_internal.email,
            applet_id=applet.id,
            applet_name=applet.display_name,
            role=invitation_internal.role,
            status=invitation_internal.status,
            key=invitation_internal.key,
            user_id=invitation_internal.user_id,
        )

    def _get_invitation_url_by_role(self, role: Role):
        domain = settings.service.urls.frontend.web_base
        url_path = settings.service.urls.frontend.invitation_send
        # TODO: uncomment when it will be needed
        # if Role.RESPONDENT != role:
        #     domain = settings.service.urls.frontend.admin_base
        return f"https://{domain}/{url_path}"

    async def _is_validated_role_for_invitation(
        self,
        applet_id: uuid.UUID,
        request_role: Role | ManagersRole,
    ):
        access_service = UserAppletAccessService(
            self.session, self._user.id, applet_id
        )
        role = None
        if request_role in [Role.RESPONDENT, Role.REVIEWER]:
            role = await access_service.get_respondent_managers_role()
        elif request_role in [
            Role.MANAGER,
            Role.COORDINATOR,
            Role.EDITOR,
        ]:
            role = await access_service.get_organizers_role()

        if not role:
            # Does not have access to send invitation
            raise DoesNotHaveAccess(
                message="You do not have access to send invitation."
            )

    async def _is_secret_user_id_unique(
        self, applet_id: uuid.UUID, secret_user_id: str, email: str | None
    ):

        workers = [
            UserAppletAccessCRUD(
                self.session
            ).get_by_secret_user_id_for_applet(applet_id, secret_user_id),
            SubjectsCrud(self.session).is_secret_id_exist(
                secret_user_id, applet_id, email
            ),
        ]

        if email:
            workers += [
                InvitationCRUD(self.session).get_for_respondent(
                    applet_id,
                    secret_user_id,
                    InvitationStatus.PENDING,
                    invited_email=email,
                )
            ]
        results = await asyncio.gather(*workers)
        if any(results):
            raise NonUniqueValue()

    async def _do_respondents_exist(
        self,
        applet_id: uuid.UUID,
        respondents: list[uuid.UUID],
    ):
        exist_respondents = await UserAppletAccessCRUD(
            self.session
        ).get_user_id_applet_and_role(
            applet_id=applet_id,
            role=Role.RESPONDENT,
        )

        for respondent in respondents:
            if respondent not in exist_respondents:
                raise RespondentDoesNotExist()

    async def accept(self, key: uuid.UUID):
        invitation = await InvitationCRUD(self.session).get_by_email_and_key(
            self._user.email_encrypted, key  # type: ignore[arg-type]
        )
        if not invitation:
            raise InvitationDoesNotExist()

        if invitation.status != InvitationStatus.PENDING:
            raise InvitationAlreadyProcessed()

        await UserAppletAccessService(
            self.session, self._user.id, invitation.applet_id
        ).add_role_by_invitation(invitation)

        await InvitationCRUD(self.session).approve_by_id(
            invitation.id, self._user.id
        )

    async def decline(self, key: uuid.UUID):
        invitation = await InvitationCRUD(self.session).get_by_email_and_key(
            self._user.email_encrypted, key  # type: ignore[arg-type]
        )
        if not invitation:
            raise InvitationDoesNotExist()

        if invitation.status != InvitationStatus.PENDING:
            raise InvitationAlreadyProcessed()

        await InvitationCRUD(self.session).decline_by_id(
            invitation.id, self._user.id
        )

    async def clear_applets_invitations(self, applet_id: uuid.UUID):
        await InvitationCRUD(self.session).delete_by_applet_id(applet_id)

    async def delete_for_managers(self, applet_ids: list[uuid.UUID]):
        roles = [
            Role.MANAGER,
            Role.COORDINATOR,
            Role.EDITOR,
            Role.REVIEWER,
        ]
        await InvitationCRUD(self.session).delete_by_applet_ids(
            self._user.email_encrypted, applet_ids, roles
        )

    async def delete_for_respondents(self, applet_ids: list[uuid.UUID]):
        roles = [
            Role.RESPONDENT,
        ]
        await InvitationCRUD(self.session).delete_by_applet_ids(
            self._user.email, applet_ids, roles
        )

    @staticmethod
    def _get_email_template_name(
        invited_user_id: uuid.UUID | None, language: str
    ) -> str:
        if not invited_user_id:
            return f"invitation_new_user_{language}"
        return f"invitation_registered_user_{language}"

    async def raise_for_secret_id(
        self,
        applet_id: uuid.UUID,
        email: str | None,
        secret_user_id: str,
        alias: str,
    ):
        try:
            await self._is_secret_user_id_unique(
                applet_id, secret_user_id, email
            )
        except NonUniqueValue as e:
            wrapper = ErrorWrapper(ValueError(e), ("body", alias))
            raise RequestValidationError([wrapper]) from e

    async def get_meta(self, key: uuid.UUID) -> dict | None:
        return await InvitationCRUD(self.session).get_meta(key)


class PrivateInvitationService:
    def __init__(self, session):
        self.session = session

    async def get_invitation(
        self, link: uuid.UUID
    ) -> PrivateInvitationDetail | None:
        applet = await PublicAppletService(self.session).get_by_link(
            link, True
        )
        if not applet:
            raise InvitationDoesNotExist()
        return PrivateInvitationDetail(
            id=applet.id,
            applet_id=applet.id,
            status=InvitationStatus.PENDING,
            applet_name=applet.display_name,
            role=Role.RESPONDENT,
            key=link,
        )

    async def accept_invitation(self, user: User, link: uuid.UUID):
        applet = await PublicAppletService(self.session).get_by_link(
            link, True
        )
        if not applet:
            raise InvitationDoesNotExist()
        await UserAppletAccessService(
            self.session, user.id, applet.id
        ).add_role_by_private_invitation(Role.RESPONDENT, user)
