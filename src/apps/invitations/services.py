import uuid

from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.domain import ManagersRole, Role
from apps.applets.service import AppletService, UserAppletAccessService
from apps.applets.service.applet_service import PublicAppletService
from apps.invitations.constants import InvitationStatus
from apps.invitations.crud import InvitationCRUD
from apps.invitations.db import InvitationSchema
from apps.invitations.domain import (
    Invitation,
    InvitationDetail,
    InvitationDetailForManagers,
    InvitationDetailForRespondent,
    InvitationDetailForReviewer,
    InvitationManagersRequest,
    InvitationRequest,
    InvitationRespondentRequest,
    InvitationReviewerRequest,
    PrivateInvitationDetail,
    RespondentMeta,
    ReviewerMeta,
)
from apps.invitations.errors import (
    AppletDoesNotExist,
    DoesNotHaveAccess,
    InvitationAlreadyProcesses,
    InvitationDoesNotExist,
    NonUniqueValue,
    RespondentDoesNotExist,
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
            "coordinator_name": f"{self._user.first_name} "
            f"{self._user.last_name}",
            "user_name": f"{user.first_name} {user.last_name}",
            "applet": applet.display_name,
            "role": invitation.role,
            "key": invitation.key,
            "email": invitation.email,
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
        )

    async def send_respondent_invitation(
        self, applet_id: int, schema: InvitationRespondentRequest
    ) -> InvitationDetailForRespondent:

        await self._is_applet_exist(applet_id)
        await self._validate_role_for_invitation(applet_id, Role.RESPONDENT)
        await self._is_secret_user_id_unique(applet_id, schema.secret_user_id)

        # TODO: Need information - should we check for already sent invite?
        #  Should we remove duplicate invites?
        #  Should we check if the user already has these rights?

        meta = RespondentMeta(
            secret_user_id=schema.secret_user_id,
            nickname=schema.nickname,
        ).dict(by_alias=True)

        invitation_schema = await InvitationCRUD().save(
            InvitationSchema(
                email=schema.email,
                applet_id=applet_id,
                role=Role.RESPONDENT,
                key=uuid.uuid3(uuid.uuid4(), schema.email),
                invitor_id=self._user.id,
                status=InvitationStatus.PENDING,
                meta=meta,
            )
        )

        invitation = Invitation.from_orm(invitation_schema)
        applet = await AppletsCRUD().get_by_id(invitation.applet_id)

        # Send email to the user
        service: MailingService = MailingService()

        html_payload: dict = {
            "coordinator_name": f"{self._user.first_name} "
            f"{self._user.last_name}",
            "user_name": f"{schema.first_name} {schema.last_name}",
            "applet": applet.display_name,
            "role": invitation.role,
            "key": invitation.key,
            "email": invitation.email,
            "link": self._get_invitation_url_by_role(invitation.role),
        }

        if schema.language == "fr":
            path = "invitation_fr"
        else:
            path = "invitation_en"

        message = MessageSchema(
            recipients=[schema.email],
            subject="Invitation to the FCM",
            body=service.get_template(path=path, **html_payload),
        )

        await service.send(message)

        return InvitationDetailForRespondent(
            id=invitation.id,
            secret_user_id=schema.secret_user_id,
            nickname=schema.nickname,
            applet_id=applet.id,
            applet_name=applet.display_name,
            role=invitation.role,
            status=invitation.status,
            key=invitation.key,
        )

    async def send_reviewer_invitation(
        self, applet_id: int, schema: InvitationReviewerRequest
    ) -> InvitationDetailForReviewer:

        await self._is_applet_exist(applet_id)
        await self._validate_role_for_invitation(applet_id, Role.REVIEWER)
        await self._is_respondents_exist(applet_id, schema.respondents)

        # TODO: Need information - should we check for already sent invite?
        #  Should we remove duplicate invites?
        #  Should we check if the user already has these rights?

        meta = ReviewerMeta(respondents=schema.respondents).dict(by_alias=True)

        invitation_schema = await InvitationCRUD().save(
            InvitationSchema(
                email=schema.email,
                applet_id=applet_id,
                role=Role.REVIEWER,
                key=uuid.uuid3(uuid.uuid4(), schema.email),
                invitor_id=self._user.id,
                status=InvitationStatus.PENDING,
                meta=meta,
            )
        )

        invitation = Invitation.from_orm(invitation_schema)
        applet = await AppletsCRUD().get_by_id(invitation.applet_id)

        # Send email to the user
        service: MailingService = MailingService()

        html_payload: dict = {
            "coordinator_name": f"{self._user.first_name} "
            f"{self._user.last_name}",
            "user_name": f"{schema.first_name} {schema.last_name}",
            "applet": applet.display_name,
            "role": invitation.role,
            "key": invitation.key,
            "email": invitation.email,
            "link": self._get_invitation_url_by_role(invitation.role),
        }

        if schema.language == "fr":
            path = "invitation_fr"
        else:
            path = "invitation_en"

        message = MessageSchema(
            recipients=[schema.email],
            subject="Invitation to the FCM",
            body=service.get_template(path=path, **html_payload),
        )

        await service.send(message)

        return InvitationDetailForReviewer(
            id=invitation.id,
            email=invitation.email,
            applet_id=applet.id,
            applet_name=applet.display_name,
            role=invitation.role,
            status=invitation.status,
            key=invitation.key,
            respondents=schema.respondents,
        )

    async def send_managers_invitation(
        self, applet_id: int, schema: InvitationManagersRequest
    ) -> InvitationDetailForManagers:

        await self._is_applet_exist(applet_id)
        await self._validate_role_for_invitation(applet_id, schema.role)

        # TODO: Need information - should we check for already sent invite?
        #  Should we remove duplicate invites?
        #  Should we check if the user already has these rights?

        invitation_schema = await InvitationCRUD().save(
            InvitationSchema(
                email=schema.email,
                applet_id=applet_id,
                role=schema.role,
                key=uuid.uuid3(uuid.uuid4(), schema.email),
                invitor_id=self._user.id,
                status=InvitationStatus.PENDING,
            )
        )

        invitation = Invitation.from_orm(invitation_schema)
        applet = await AppletsCRUD().get_by_id(invitation.applet_id)

        # Send email to the user
        service: MailingService = MailingService()

        html_payload: dict = {
            "coordinator_name": f"{self._user.first_name} "
            f"{self._user.last_name}",
            "user_name": f"{schema.first_name} {schema.last_name}",
            "applet": applet.display_name,
            "role": invitation.role,
            "key": invitation.key,
            "email": invitation.email,
            "link": self._get_invitation_url_by_role(invitation.role),
        }

        if schema.language == "fr":
            path = "invitation_fr"
        else:
            path = "invitation_en"

        message = MessageSchema(
            recipients=[schema.email],
            subject="Invitation to the FCM",
            body=service.get_template(path=path, **html_payload),
        )

        await service.send(message)

        return InvitationDetailForManagers(
            id=invitation.id,
            email=invitation.email,
            applet_id=applet.id,
            applet_name=applet.display_name,
            role=invitation.role,
            status=invitation.status,
            key=invitation.key,
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

    async def _is_applet_exist(
        self,
        applet_id: int,
    ):
        exist = await AppletService(self._user.id).exist_by_id(applet_id)
        if not exist:
            raise AppletDoesNotExist(
                f"Applet by id {applet_id} does not exist."
            )

    # invitation_request
    async def _validate_role_for_invitation(
        self, applet_id: int, request_role: Role | ManagersRole
    ):

        access_service = UserAppletAccessService(self._user.id, applet_id)
        if request_role == Role.RESPONDENT:
            role = await access_service.get_respondent_managers_role()
        elif request_role in [
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
                f"role {request_role.name}."
            )

        if not role:
            # Does not have access to send invitation
            raise DoesNotHaveAccess(
                message="You do not have access to send invitation."
            )
        elif Role(role) < Role(request_role):
            # TODO: remove this validation if it is not needed
            # Can not invite users by roles where own role level is lower.
            raise DoesNotHaveAccess(
                message="You do not have access to send invitation."
            )

    async def _is_secret_user_id_unique(
        self,
        applet_id: int,
        secret_user_id: str,
    ):
        meta = await UserAppletAccessCRUD().get_meta_applet_and_role(
            applet_id=applet_id,
            role=Role.RESPONDENT,
        )
        if meta:
            for item in meta:
                if item["secretUserId"] == secret_user_id:
                    raise NonUniqueValue(
                        message=f"In applet with id {applet_id} "
                        f"secret User Id is non-unique."
                    )

    async def _is_respondents_exist(
        self,
        applet_id: int,
        respondents: list[int],
    ):
        exist_respondents = (
            await UserAppletAccessCRUD().get_user_id_applet_and_role(
                applet_id=applet_id,
                role=Role.RESPONDENT,
            )
        )

        for respondent in respondents:
            if respondent not in exist_respondents:
                raise RespondentDoesNotExist(
                    message=f"Respondent with id {respondent} not exist "
                    f"in applet with id {applet_id}."
                )

    async def accept(self, key: uuid.UUID):
        invitation = await InvitationCRUD().get_by_email_and_key(
            self._user.email, key
        )
        if not invitation:
            raise InvitationDoesNotExist()

        if invitation.status != InvitationStatus.PENDING:
            raise InvitationAlreadyProcesses()

        if type(invitation.meta) == dict:
            await UserAppletAccessService(
                self._user.id, invitation.applet_id
            ).add_role(invitation.role, invitation.meta)
        else:
            await UserAppletAccessService(
                self._user.id, invitation.applet_id
            ).add_role(invitation.role, invitation.meta.dict(by_alias=True))

        await InvitationCRUD().approve_by_id(invitation.id)
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


class PrivateInvitationService:
    async def get_invitation(
        self, link: uuid.UUID
    ) -> PrivateInvitationDetail | None:
        applet = await PublicAppletService().get_by_link(link, True)
        if not applet:
            return None
        return PrivateInvitationDetail(
            id=applet.id,
            applet_id=applet.id,
            status=InvitationStatus.PENDING,
            applet_name=applet.display_name,
            role=Role.RESPONDENT,
            key=link,
            title=None,
            body=None,
        )

    async def accept_invitation(self, user_id: uuid.UUID, link: uuid.UUID):
        applet = await PublicAppletService().get_by_link(link, True)
        if not applet:
            raise InvitationDoesNotExist()
        await UserAppletAccessService(user_id, applet.id).add_role(
            Role.RESPONDENT
        )
