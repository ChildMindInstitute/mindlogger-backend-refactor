import asyncio
import uuid

from fastapi.exceptions import RequestValidationError
from pydantic.error_wrappers import ErrorWrapper

from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.db.schemas import AppletSchema
from apps.applets.domain import ManagersRole, Role
from apps.applets.service import AppletService, UserAppletAccessService
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
    InvitationRequest,
    InvitationRespondent,
    InvitationRespondentRequest,
    InvitationReviewer,
    InvitationReviewerRequest,
    PrivateInvitationDetail,
    RespondentMeta,
    ReviewerMeta,
    _InvitationRequest,
)
from apps.invitations.errors import (
    AppletDoesNotExist,
    DoesNotHaveAccess,
    InvitationAlreadyProcesses,
    InvitationDoesNotExist,
    ManagerInvitationExist,
    NonUniqueValue,
    RespondentDoesNotExist,
    RespondentInvitationExist,
)
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.shared.query_params import QueryParams
from apps.users import UserNotFound, UsersCRUD
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

    async def fetch_all_for_invited(
        self, query_params: QueryParams
    ) -> list[InvitationDetail]:
        return await self.invitations_crud.get_pending_by_invited_email(
            self._user.email, query_params
        )

    async def fetch_all_for_invited_count(
        self, query_params: QueryParams
    ) -> int:
        return await self.invitations_crud.get_pending_by_invited_email_count(
            self._user.email, query_params
        )

    async def get(self, key: uuid.UUID) -> InvitationDetailGeneric | None:
        invitation = await self.invitations_crud.get_by_email_and_key(
            self._user.email_encrypted, key  # type: ignore[arg-type]
        )
        if not invitation:
            raise InvitationDoesNotExist(
                message=f"No such invitation with key={key}."
            )
        elif invitation.status != InvitationStatus.PENDING:
            raise InvitationAlreadyProcesses()
        return invitation

    def _get_invitation_subject(self, applet: AppletSchema):
        return f"{applet.display_name} invitation"

    async def send_respondent_invitation(
        self, applet_id: uuid.UUID, schema: InvitationRespondentRequest
    ) -> InvitationDetailForRespondent:

        await self._is_validated_role_for_invitation(
            applet_id, Role.RESPONDENT, schema
        )
        try:
            await self._is_secret_user_id_unique(
                applet_id, schema.secret_user_id
            )
        except NonUniqueValue as e:
            field_name = InvitationRespondentRequest.__fields__[
                "secret_user_id"
            ].alias
            wrapper = ErrorWrapper(ValueError(e), ("body", field_name))
            raise RequestValidationError([wrapper]) from e

        # Get all invitations and check if it is possible to create
        # the another invite or update existing or invitation
        # has already been accepted by the user, and we should raise
        # an error that sending a second invitation is not possible.
        invitations = (
            await self.invitations_crud.get_by_email_applet_role_respondent(
                email_=schema.email, applet_id_=applet_id
            )
        )

        success_invitation_schema = {
            "email": schema.email,
            "applet_id": applet_id,
            "role": Role.RESPONDENT,
            "key": uuid.uuid3(uuid.uuid4(), schema.email),
            "invitor_id": self._user.id,
            "status": InvitationStatus.PENDING,
            "first_name": schema.first_name,
            "last_name": schema.last_name,
        }

        payload = None
        invitation_schema = None
        for invitation in invitations:
            meta = RespondentMeta.from_orm(invitation.meta)
            if invitation.status == InvitationStatus.PENDING and (
                meta.secret_user_id == schema.secret_user_id
            ):
                payload = success_invitation_schema | {"meta": meta.dict()}
                invitation_schema = await self.invitations_crud.update(
                    lookup="id",
                    value=invitation.id,
                    schema=InvitationSchema(**payload),
                )
                break
            elif invitation.status == InvitationStatus.APPROVED and (
                meta.secret_user_id == schema.secret_user_id
            ):
                raise InvitationAlreadyProcesses

        if not payload:
            meta = RespondentMeta(
                secret_user_id=schema.secret_user_id,
                nickname=schema.nickname,
            )

            payload = success_invitation_schema | {"meta": meta.dict()}
            invitation_schema = await self.invitations_crud.save(
                InvitationSchema(**payload)
            )
            invitation_internal: InvitationRespondent = (
                InvitationRespondent.from_orm(invitation_schema)
            )
        else:
            invitation_internal = InvitationRespondent.from_orm(
                invitation_schema
            )

        applet = await AppletsCRUD(self.session).get_by_id(
            invitation_internal.applet_id
        )

        try:
            await UsersCRUD(self.session).get_by_email(schema.email)
        except UserNotFound:
            path = "invitation_new_user_en"
        else:
            path = "invitation_registered_user_en"

        # Send email to the user
        service = MailingService()
        message = MessageSchema(
            recipients=[schema.email],
            subject=self._get_invitation_subject(applet),
            body=service.get_template(
                path=path,
                first_name=schema.first_name,
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
        )

    async def send_reviewer_invitation(
        self, applet_id: uuid.UUID, schema: InvitationReviewerRequest
    ) -> InvitationDetailForReviewer:

        await self._is_validated_role_for_invitation(
            applet_id, Role.REVIEWER, schema
        )
        await self._is_respondents_exist(applet_id, schema.respondents)

        # Get all invitations and check if it is possible to create
        # the another invite or update existing or invitation
        # has already been accepted by the user, and we should raise
        # an error that sending a second invitation is not possible.
        invitations: list[
            InvitationReviewer
        ] = await self.invitations_crud.get_by_email_applet_role_reviewer(
            email_=schema.email, applet_id_=applet_id
        )
        respondents = [
            str(respondent_id) for respondent_id in schema.respondents
        ]

        success_invitation_schema = {
            "email": schema.email,
            "applet_id": applet_id,
            "role": Role.REVIEWER,
            "key": uuid.uuid3(uuid.uuid4(), schema.email),
            "invitor_id": self._user.id,
            "status": InvitationStatus.PENDING,
            "first_name": schema.first_name,
            "last_name": schema.last_name,
        }

        payload = None
        invitation_schema = None
        for invitation in invitations:
            meta = ReviewerMeta.from_orm(invitation.meta)
            if invitation.status == InvitationStatus.PENDING and (
                meta.respondents == respondents
            ):
                payload = success_invitation_schema | {"meta": meta.dict()}
                invitation_schema = await self.invitations_crud.update(
                    lookup="id",
                    value=invitation.id,
                    schema=InvitationSchema(**payload),
                )
                break
            elif invitation.status == InvitationStatus.APPROVED and (
                meta.respondents == respondents
            ):
                raise InvitationAlreadyProcesses

        if not payload:
            meta = ReviewerMeta(respondents=respondents)

            payload = success_invitation_schema | {"meta": meta.dict()}
            invitation_schema = await self.invitations_crud.save(
                InvitationSchema(**payload)
            )
            invitation_internal: InvitationReviewer = (
                InvitationReviewer.from_orm(invitation_schema)
            )
        else:
            invitation_internal = InvitationReviewer.from_orm(
                invitation_schema
            )

        applet = await AppletsCRUD(self.session).get_by_id(
            invitation_internal.applet_id
        )

        try:
            await UsersCRUD(self.session).get_by_email(schema.email)
        except UserNotFound:
            path = "invitation_new_user_en"
        else:
            path = "invitation_registered_user_en"

        # Send email to the user
        service = MailingService()
        message = MessageSchema(
            recipients=[schema.email],
            subject=self._get_invitation_subject(applet),
            body=service.get_template(
                path=path,
                first_name=schema.first_name,
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

        await WorkspaceService(
            self.session, self._user.id
        ).update_workspace_name(self._user, schema.workspace_prefix)

        return InvitationDetailForReviewer(
            id=invitation_internal.id,
            email=invitation_internal.email,
            applet_id=applet.id,
            applet_name=applet.display_name,
            role=invitation_internal.role,
            status=invitation_internal.status,
            key=invitation_internal.key,
            respondents=schema.respondents,
        )

    async def send_managers_invitation(
        self, applet_id: uuid.UUID, schema: InvitationManagersRequest
    ) -> InvitationDetailForManagers:

        await self._is_validated_role_for_invitation(
            applet_id, schema.role, schema
        )

        # Get all invitations and check if it is possible to create
        # the another invite or update existing or invitation
        # has already been accepted by the user, and we should raise
        # an error that sending a second invitation is not possible.
        invitations: list[
            InvitationManagers
        ] = await self.invitations_crud.get_by_email_applet_role_managers(
            email_=schema.email, applet_id_=applet_id, role_=schema.role
        )

        success_invitation_schema = {
            "email": schema.email,
            "applet_id": applet_id,
            "role": schema.role,
            "key": uuid.uuid3(uuid.uuid4(), schema.email),
            "invitor_id": self._user.id,
            "status": InvitationStatus.PENDING,
            "first_name": schema.first_name,
            "last_name": schema.last_name,
        }

        payload = None
        invitation_schema = None
        for invitation in invitations:
            if invitation.status == InvitationStatus.PENDING:
                payload = success_invitation_schema | {"meta": {}}
                invitation_schema = await self.invitations_crud.update(
                    lookup="id",
                    value=invitation.id,
                    schema=InvitationSchema(**payload),
                )
                break
            elif invitation.status == InvitationStatus.APPROVED:
                raise InvitationAlreadyProcesses

        if not payload:
            payload = success_invitation_schema | {"meta": {}}
            invitation_schema = await self.invitations_crud.save(
                InvitationSchema(**payload)
            )
            invitation_internal: InvitationManagers = (
                InvitationManagers.from_orm(invitation_schema)
            )
        else:
            invitation_internal = InvitationManagers.from_orm(
                invitation_schema
            )

        applet = await AppletsCRUD(self.session).get_by_id(
            invitation_internal.applet_id
        )

        try:
            await UsersCRUD(self.session).get_by_email(schema.email)
        except UserNotFound:
            path = "invitation_new_user_en"
        else:
            path = "invitation_registered_user_en"

        # Send email to the user
        service = MailingService()
        message = MessageSchema(
            recipients=[schema.email],
            subject=self._get_invitation_subject(applet),
            body=service.get_template(
                path=path,
                first_name=schema.first_name,
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

        await WorkspaceService(
            self.session, self._user.id
        ).update_workspace_name(self._user, schema.workspace_prefix)

        return InvitationDetailForManagers(
            id=invitation_internal.id,
            email=invitation_internal.email,
            applet_id=applet.id,
            applet_name=applet.display_name,
            role=invitation_internal.role,
            status=invitation_internal.status,
            key=invitation_internal.key,
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
        is_exist = await AppletService(
            self.session, self._user.id
        ).exist_by_id(invitation_request.applet_id)
        if not is_exist:
            raise AppletDoesNotExist()

        access_service = UserAppletAccessService(
            self.session, self._user.id, invitation_request.applet_id
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

    async def _is_validated_role_for_invitation(
        self,
        applet_id: uuid.UUID,
        request_role: Role | ManagersRole,
        schema: _InvitationRequest,
    ):
        access_service = UserAppletAccessService(
            self.session, self._user.id, applet_id
        )
        if request_role == Role.RESPONDENT:
            role = await access_service.get_respondent_managers_role()
        elif request_role in [
            Role.MANAGER,
            Role.COORDINATOR,
            Role.EDITOR,
        ]:
            role = await access_service.get_organizers_role()
        elif request_role == Role.REVIEWER:
            role = await access_service.get_respondent_managers_role()
            if (
                role == Role.COORDINATOR
                and self._user.email.lower() == schema.email.lower()
            ):
                role = None
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
        applet_id: uuid.UUID,
        secret_user_id: str,
    ):
        access_coro = UserAppletAccessCRUD(
            self.session
        ).get_by_secret_user_id_for_applet(applet_id, secret_user_id)
        invitation_coro = InvitationCRUD(self.session).get_for_respondent(
            applet_id, secret_user_id, InvitationStatus.PENDING
        )
        access, invitation = await asyncio.gather(access_coro, invitation_coro)
        if access or invitation:
            raise NonUniqueValue(
                message=f"In applet with id {applet_id} "
                f"secret User Id is non-unique."
            )

    async def _is_respondents_exist(
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
                raise RespondentDoesNotExist(
                    message=f"Respondent with id {respondent} not exist "
                    f"in applet with id {applet_id}."
                )

    async def accept(self, key: uuid.UUID):
        invitation = await InvitationCRUD(self.session).get_by_email_and_key(
            self._user.email_encrypted, key  # type: ignore[arg-type]
        )
        if not invitation:
            raise InvitationDoesNotExist()

        if invitation.status != InvitationStatus.PENDING:
            raise InvitationAlreadyProcesses()

        await UserAppletAccessService(
            self.session, self._user.id, invitation.applet_id
        ).add_role_by_invitation(invitation)

        await InvitationCRUD(self.session).approve_by_id(invitation.id)

    async def decline(self, key: uuid.UUID):
        invitation = await InvitationCRUD(self.session).get_by_email_and_key(
            self._user.email_encrypted, key  # type: ignore[arg-type]
        )
        if not invitation:
            raise InvitationDoesNotExist()

        if invitation.status != InvitationStatus.PENDING:
            raise InvitationAlreadyProcesses()

        await InvitationCRUD(self.session).decline_by_id(invitation.id)

    async def clear_applets_invitations(self, applet_id: uuid.UUID):
        await InvitationCRUD(self.session).delete_by_applet_id(applet_id)

    async def exist(self, email: str, role: str, applet_id: uuid.UUID) -> int:
        return await InvitationCRUD(self.session).exist(email, role, applet_id)

    async def check_for_duplicates(
        self, applet_id: uuid.UUID, email: str, role: str
    ):
        is_exist = await InvitationCRUD(self.session).duplicate_exist(
            email, role, applet_id
        )
        if is_exist and role in Role.managers():
            raise ManagerInvitationExist()
        elif is_exist:
            raise RespondentInvitationExist()


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
            return None
        return PrivateInvitationDetail(
            id=applet.id,
            applet_id=applet.id,
            status=InvitationStatus.PENDING,
            applet_name=applet.display_name,
            role=Role.RESPONDENT,
            key=link,
        )

    async def accept_invitation(self, user_id: uuid.UUID, link: uuid.UUID):
        applet = await PublicAppletService(self.session).get_by_link(
            link, True
        )
        if not applet:
            raise InvitationDoesNotExist()
        await UserAppletAccessService(
            self.session, user_id, applet.id
        ).add_role_by_private_invitation(Role.RESPONDENT)
