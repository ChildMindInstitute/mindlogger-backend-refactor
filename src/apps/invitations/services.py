import uuid

from apps.applets.crud import AppletsCRUD
from apps.applets.domain import Role
from apps.applets.service import AppletService, UserAppletAccessService
from apps.invitations.constants import InvitationStatus
from apps.invitations.crud import InvitationCRUD
from apps.invitations.db import InvitationSchema
from apps.invitations.domain import (
    Invitation,
    InvitationDetail,
    InvitationRequest,
)
from apps.invitations.errors import (
    AppletDoesNotExist,
    DoesNotHaveAccess,
    InvitationAlreadyProcesses,
    InvitationDoesNotExist,
)
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.users import UsersCRUD
from apps.users.domain import User
from config import settings


class InvitationsService:
    def __init__(self, user: User):
        self._user: User = user

    async def fetch_all(self) -> list[InvitationDetail]:
        return await InvitationCRUD().get_pending_by_invitor_id(self._user.id)

    async def get(self, key: str) -> InvitationDetail | None:
        return await InvitationCRUD().get_by_email_and_key(
            self._user.email, uuid.UUID(key)
        )

    async def get_private_invitation(
        self, link: uuid.UUID
    ) -> InvitationDetail | None:
        applet = await AppletService(self._user.id).get_by_link(link, True)
        if not applet:
            return None
        return InvitationDetail(
            id=applet.id,
            email=self._user.email,
            applet_id=applet.id,
            status=InvitationStatus.PENDING,
            applet_name=applet.display_name,
            role=Role.RESPONDENT,
            key=link,
            title=None,
            body=None,
        )

    async def send_invitation(
        self, schema: InvitationRequest
    ) -> InvitationDetail:
        await self._validate_invitation(schema)

        invitation_schema = await InvitationCRUD().save(
            InvitationSchema(
                email=schema.email,
                applet_id=schema.applet_id,
                role=schema.role,
                key=uuid.uuid3(uuid.uuid4(), schema.email),
                invitor_id=self._user.id,
                title=schema.title,
                body=schema.body,
                status=InvitationStatus.PENDING,
            )
        )

        invitation = Invitation.from_orm(invitation_schema)
        applet = await AppletsCRUD().get_by_id(invitation.applet_id)

        # Send email to the user
        service: MailingService = MailingService()

        # FIXME: user is not mandatory, as invite can be
        #  sent to non-registered user
        user: User = await UsersCRUD().get_by_email(schema.email)

        html_payload: dict = {
            "coordinator_name": self._user.full_name,
            "user_name": user.full_name,
            "applet": applet.display_name,
            "role": invitation.role,
            "key": invitation.key,
            "email": invitation.email,
            "title": invitation.title,
            "body": invitation.body,
            "link": self._get_invitation_url_by_role(invitation.role),
        }
        message = MessageSchema(
            recipients=[schema.email],
            subject="Invitation to the FCM",
            body=service.get_template(path="invitation", **html_payload),
        )

        await service.send(message)

        return InvitationDetail(
            id=invitation.id,
            email=invitation.email,
            applet_id=applet.id,
            applet_name=applet.display_name,
            role=invitation.role,
            status=invitation.status,
            key=invitation.key,
            title=invitation.title,
            body=invitation.body,
        )

    def _get_invitation_url_by_role(self, role: Role):
        domain = settings.service.urls.frontend.web_base
        url_path = settings.service.urls.frontend.invitation_send
        # TODO: uncomment when it will be needed
        # if Role.RESPONDENT != role:
        #     domain = settings.service.urls.frontend.admin_base
        return f"https://{domain}/{url_path}"

    async def _validate_invitation(
        self, invitation_request: InvitationRequest
    ):
        is_exist = await AppletService(self._user.id).exist_by_id(
            invitation_request.applet_id
        )
        if not is_exist:
            raise AppletDoesNotExist(
                f"Applet by id {invitation_request.applet_id} does not exist."
            )

        access_service = UserAppletAccessService(
            self._user.id, invitation_request.applet_id
        )
        if invitation_request.role == Role.RESPONDENT:
            role = await access_service.get_respondent_managers_role()
        elif invitation_request.role in [
            Role.MANAGER,
            Role.COORDINATOR,
            Role.EDITOR,
            Role.REVIEWER,
        ]:
            role = await access_service.get_organizers_role()
        else:
            # Wrong role to invite
            raise DoesNotHaveAccess(
                message="You can not invite user with "
                f"role {invitation_request.role.name}."
            )

        if not role:
            # Does not have access to send invitation
            raise DoesNotHaveAccess(
                message="You do not have access to send invitation."
            )
        elif Role(role) < Role(invitation_request.role):
            # TODO: remove this validation if it is not needed
            # Can not invite users by roles where own role level is lower.
            raise DoesNotHaveAccess(
                message="You do not have access to send invitation."
            )

    async def accept(self, key: uuid.UUID):
        invitation = await InvitationCRUD().get_by_email_and_key(
            self._user.email, key
        )
        if not invitation:
            raise InvitationDoesNotExist()

        if invitation.status != InvitationStatus.PENDING:
            raise InvitationAlreadyProcesses()

        await UserAppletAccessService(
            self._user.id, invitation.applet_id
        ).add_role(invitation.role)

        await InvitationCRUD().approve_by_id(invitation.id)
        return

    async def accept_private_invitation(self, link: uuid.UUID):
        applet = await AppletService(self._user.id).get_by_link(link, True)
        if not applet:
            raise InvitationDoesNotExist()
        await UserAppletAccessService(self._user.id, applet.id).add_role(
            Role.RESPONDENT
        )
        return

    async def decline(self, key: uuid.UUID):
        invitation = await InvitationCRUD().get_by_email_and_key(
            self._user.email, key
        )
        if not invitation:
            raise InvitationDoesNotExist()

        if invitation.status != InvitationStatus.PENDING:
            raise InvitationAlreadyProcesses()

        await InvitationCRUD().decline_by_id(invitation.id)
