import asyncio
import uuid
from typing import cast

from apps.activity_assignments.service import ActivityAssignmentService
from apps.applets.crud import AppletsCRUD
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
    InvitationSubjectAcceptError,
)
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.shared.exception import ValidationError
from apps.shared.query_params import QueryParams
from apps.subjects.constants import SubjectTag
from apps.subjects.crud import SubjectsCrud
from apps.subjects.domain import Subject
from apps.subjects.errors import AppletUserViolationError
from apps.users import UsersCRUD
from apps.users.domain import User
from apps.workspaces.domain.workspace import WorkspaceRespondent
from apps.workspaces.service.user_access import UserAccessService
from apps.workspaces.service.workspace import WorkspaceService
from config import settings


class InvitationsService:
    def __init__(self, session, user: User):
        self._user: User = user
        self.invitations_crud = InvitationCRUD(session)
        self.session = session

    async def fetch_all(self, query_params: QueryParams) -> list[InvitationDetail]:
        return await self.invitations_crud.get_pending_by_invitor_id(self._user.id, query_params)

    async def fetch_by_emails(self, emails: list[str]) -> dict[str, InvitationDetail]:
        return await self.invitations_crud.get_latest_by_emails(emails)

    async def fill_pending_invitations_respondents(
        self, respondents: list[WorkspaceRespondent]
    ) -> list[WorkspaceRespondent]:
        emails = [respondent.email for respondent in respondents if respondent.email is not None]
        invitations = await self.fetch_by_emails(emails)

        for respondent in respondents:
            for detail in respondent.details or []:
                detail.invitation = invitations.get(f"{respondent.email}_{detail.applet_id}")

        return respondents

    async def fetch_all_count(self, query_params: QueryParams) -> int:
        return await self.invitations_crud.get_pending_by_invitor_id_count(self._user.id, query_params)

    async def get(self, key: uuid.UUID) -> InvitationDetailGeneric | None:
        self._user.email_encrypted = cast(str, self._user.email_encrypted)
        invitation = await self.invitations_crud.get_by_email_and_key(
            self._user.email_encrypted,
            key,
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
        subject: Subject,
    ) -> InvitationDetailForRespondent:
        await self._is_validated_role_for_invitation(applet_id, Role.RESPONDENT)

        subject_invitation = await self.invitations_crud.get_pending_subject_invitation(applet_id, subject.id)
        if subject_invitation and subject_invitation.email != schema.email:
            raise ValidationError("Subject already invited with different email.")

        # Get invited user if he exists. User will be linked with invitaion
        # by user_id in this case
        invited_user = await UsersCRUD(self.session).get_user_or_none_by_email(email=schema.email)
        invited_user_id = invited_user.id if invited_user is not None else None
        if invited_user_id:
            await UserAppletAccessService(self.session, self._user.id, applet_id).unpin(
                pinned_user_id=invited_user_id, pinned_subject_id=None
            )

        meta = RespondentMeta(subject_id=str(subject.id))
        payload = {
            "email": schema.email,
            "applet_id": applet_id,
            "role": Role.RESPONDENT,
            "key": uuid.uuid3(uuid.uuid4(), schema.email),
            "invitor_id": self._user.id,
            "status": InvitationStatus.PENDING,
            "user_id": invited_user_id,
            "meta": meta.dict(),
            "tag": schema.tag,
        }
        pending_invitation = await self.invitations_crud.get_pending_invitation(schema.email, applet_id)
        if pending_invitation:
            invitation_schema = await self.invitations_crud.update(
                lookup="id",
                value=pending_invitation.id,
                schema=InvitationSchema(**payload),
            )
        else:
            invitation_schema = await self.invitations_crud.save(InvitationSchema(**payload))
        invitation_internal: InvitationRespondent = InvitationRespondent.from_orm(invitation_schema)

        applet = await AppletsCRUD(self.session).get_by_id(invitation_internal.applet_id)

        # Send email to the user
        service = MailingService()
        message = MessageSchema(
            recipients=[schema.email],
            subject=self._get_invitation_subject(applet),
            body=service.get_localized_html_template(
                template_name=self._get_email_template_name(invited_user_id),
                language=schema.language,
                first_name=subject.first_name,
                last_name=subject.last_name,
                applet_name=applet.display_name,
                role=invitation_internal.role,
                link=self._get_invitation_url_by_role(invitation_internal.role),
                key=invitation_internal.key,
            ),
        )
        _ = asyncio.create_task(service.send(message))

        return InvitationDetailForRespondent(
            id=invitation_internal.id,
            secret_user_id=schema.secret_user_id,
            nickname=subject.nickname,
            applet_id=applet.id,
            applet_name=applet.display_name,
            role=invitation_internal.role,
            status=invitation_internal.status,
            first_name=subject.first_name,
            last_name=subject.last_name,
            key=invitation_internal.key,
            user_id=invitation_internal.user_id,
            tag=invitation_internal.tag,
        )

    async def send_reviewer_invitation(
        self, applet_id: uuid.UUID, schema: InvitationReviewerRequest
    ) -> InvitationDetailForReviewer:
        await self._is_validated_role_for_invitation(applet_id, Role.REVIEWER)
        await self._verify_applet_subjects(applet_id, schema.subjects)

        # Get invited user if he exists. User will be linked with invitaion
        # by user_id in this case
        invited_user = await UsersCRUD(self.session).get_user_or_none_by_email(email=schema.email)
        invited_user_id = invited_user.id if invited_user is not None else None

        meta = ReviewerMeta(subjects=list(map(str, schema.subjects or [])))
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
            "meta": meta.dict(),
            "tag": SubjectTag.TEAM,
            "title": schema.title,
        }

        pending_invitation = await self.invitations_crud.get_pending_invitation(schema.email, applet_id)
        if pending_invitation:
            invitation_schema = await self.invitations_crud.update(
                lookup="id",
                value=pending_invitation.id,
                schema=InvitationSchema(**payload),
            )
        else:
            invitation_schema = await self.invitations_crud.save(InvitationSchema(**payload))
        invitation_internal = InvitationReviewer.from_orm(invitation_schema)

        applet = await AppletsCRUD(self.session).get_by_id(invitation_internal.applet_id)

        await WorkspaceService(self.session, self._user.id).update_workspace_name(self._user, schema.workspace_prefix)

        # Send email to the user
        service = MailingService()
        message = MessageSchema(
            recipients=[schema.email],
            subject=self._get_invitation_subject(applet),
            body=service.get_localized_html_template(
                template_name=self._get_email_template_name(invited_user_id),
                language=schema.language,
                first_name=schema.first_name,
                last_name=schema.last_name,
                applet_name=applet.display_name,
                role=invitation_internal.role,
                link=self._get_invitation_url_by_role(invitation_internal.role),
                key=invitation_internal.key,
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
            first_name=invitation_internal.first_name,
            last_name=invitation_internal.last_name,
            key=invitation_internal.key,
            subjects=schema.subjects,
            user_id=invitation_internal.user_id,
            tag=invitation_internal.tag,
            title=invitation_internal.title,
        )

    async def send_managers_invitation(
        self,
        applet_id: uuid.UUID,
        schema: InvitationManagersRequest,
    ) -> InvitationDetailForManagers:
        await self._is_validated_role_for_invitation(applet_id, schema.role)
        # Get invited user if he exists. User will be linked with invitaion
        # by user_id in this case
        invited_user = await UsersCRUD(self.session).get_user_or_none_by_email(email=schema.email)
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
            "tag": SubjectTag.TEAM,
            "title": schema.title,
        }

        pending_invitation = await self.invitations_crud.get_pending_invitation(schema.email, applet_id)
        if pending_invitation:
            invitation_schema = await self.invitations_crud.update(
                lookup="id",
                value=pending_invitation.id,
                schema=InvitationSchema(**payload),
            )
        else:
            invitation_schema = await self.invitations_crud.save(InvitationSchema(**payload))
        invitation_internal = InvitationManagers.from_orm(invitation_schema)

        applet = await AppletsCRUD(self.session).get_by_id(invitation_internal.applet_id)

        await WorkspaceService(self.session, self._user.id).update_workspace_name(self._user, schema.workspace_prefix)

        # Send email to the user
        service = MailingService()
        message = MessageSchema(
            recipients=[schema.email],
            subject=self._get_invitation_subject(applet),
            body=service.get_localized_html_template(
                template_name=self._get_email_template_name(invited_user_id),
                language=schema.language,
                first_name=schema.first_name,
                last_name=schema.last_name,
                applet_name=applet.display_name,
                role=invitation_internal.role,
                link=self._get_invitation_url_by_role(invitation_internal.role),
                key=invitation_internal.key,
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
            first_name=invitation_internal.first_name,
            last_name=invitation_internal.last_name,
            key=invitation_internal.key,
            user_id=invitation_internal.user_id,
            tag=invitation_internal.tag,
            title=invitation_internal.title,
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
        access_service = UserAppletAccessService(self.session, self._user.id, applet_id)
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
            raise DoesNotHaveAccess(message="You do not have access to send invitation.")

    async def _verify_applet_subjects(
        self,
        applet_id: uuid.UUID,
        subject_ids: list[uuid.UUID],
    ):
        if subject_ids:
            existing_subject_ids = await SubjectsCrud(self.session).reduce_applet_subject_ids(applet_id, subject_ids)

            if len(existing_subject_ids) != len(subject_ids):
                raise ValidationError("Subject does not exist in applet.")

    async def accept(self, key: uuid.UUID) -> None:
        self._user.email_encrypted = cast(str, self._user.email_encrypted)
        invitation = await InvitationCRUD(self.session).get_by_email_and_key(
            self._user.email_encrypted,
            key,
        )
        if not invitation:
            raise InvitationDoesNotExist()

        if invitation.status != InvitationStatus.PENDING:
            raise InvitationAlreadyProcessed()

        try:
            await UserAppletAccessService(self.session, self._user.id, invitation.applet_id).add_role_by_invitation(
                invitation
            )
        except AppletUserViolationError:
            raise InvitationSubjectAcceptError(invitation)

        if invitation.role == Role.RESPONDENT and isinstance(invitation.meta, RespondentMeta):
            if invitation.meta.subject_id:
                await UserAccessService(self.session, self._user.id).change_subject_pins_to_user(
                    self._user.id, uuid.UUID(invitation.meta.subject_id)
                )

                await ActivityAssignmentService(self.session).check_for_assignment_and_notify(
                    applet_id=invitation.applet_id, respondent_subject_id=uuid.UUID(invitation.meta.subject_id)
                )

        await InvitationCRUD(self.session).approve_by_id(invitation.id, self._user.id)

    async def decline(self, key: uuid.UUID) -> None:
        self._user.email_encrypted = cast(str, self._user.email_encrypted)
        invitation = await InvitationCRUD(self.session).get_by_email_and_key(
            self._user.email_encrypted,
            key,
        )
        if not invitation:
            raise InvitationDoesNotExist()

        if invitation.status != InvitationStatus.PENDING:
            raise InvitationAlreadyProcessed()

        await InvitationCRUD(self.session).decline_by_id(invitation.id, self._user.id)

    async def clear_applets_invitations(self, applet_id: uuid.UUID):
        await InvitationCRUD(self.session).delete_by_applet_id(applet_id)

    async def delete_for_managers(self, applet_ids: list[uuid.UUID]):
        roles = [
            Role.MANAGER,
            Role.COORDINATOR,
            Role.EDITOR,
            Role.REVIEWER,
        ]
        await InvitationCRUD(self.session).delete_by_applet_ids(self._user.email_encrypted, applet_ids, roles)

    async def delete_for_respondents(self, applet_ids: list[uuid.UUID]):
        roles = [
            Role.RESPONDENT,
        ]
        await InvitationCRUD(self.session).delete_by_applet_ids(self._user.email, applet_ids, roles)

    @staticmethod
    def _get_email_template_name(invited_user_id: uuid.UUID | None) -> str:
        if not invited_user_id:
            return "invitation_new_user"
        return "invitation_registered_user"

    async def get_meta(self, key: uuid.UUID) -> dict | None:
        return await InvitationCRUD(self.session).get_meta(key)

    async def check_email_invited(self, email: str, applet_id: uuid.UUID) -> bool:  # TODO delete
        emails = await InvitationCRUD(self.session).get_invited_emails(applet_id)
        return bool(emails.count(email))


class PrivateInvitationService:
    def __init__(self, session):
        self.session = session

    async def get_invitation(self, link: uuid.UUID) -> PrivateInvitationDetail | None:
        applet = await PublicAppletService(self.session).get_by_link(link, is_private=True)
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
        applet = await PublicAppletService(self.session).get_by_link(link, is_private=True)
        if not applet:
            raise InvitationDoesNotExist()
        await UserAppletAccessService(self.session, user.id, applet.id).add_role_by_private_invitation(
            Role.RESPONDENT, user
        )
