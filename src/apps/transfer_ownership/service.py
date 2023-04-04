import uuid

from apps.answers.crud import AnswerActivityItemsCRUD, AnswerFlowItemsCRUD
from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.domain import Role
from apps.authentication.errors import PermissionsError
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.transfer_ownership.crud import TransferCRUD
from apps.transfer_ownership.domain import InitiateTransfer, Transfer
from apps.users.crud import UsersCRUD
from apps.users.domain import User
from apps.users.errors import UserNotFound
from apps.workspaces.db.schemas import UserAppletAccessSchema
from config import settings


class TransferService:
    def __init__(self, session, user: User):
        self._user = user
        self.session = session

    async def initiate_transfer(
        self, applet_id: uuid.UUID, transfer_request: InitiateTransfer
    ):
        """Initiate a transfer of ownership of an applet."""
        # check if user is owner of applet
        applet = await AppletsCRUD(self.session).get_by_id(id_=applet_id)

        access = await UserAppletAccessCRUD(self.session).get_applet_owner(
            applet_id
        )
        if access.user_id != self._user.id:
            raise PermissionsError()

        transfer = Transfer(
            email=transfer_request.email,
            applet_id=applet_id,
            key=uuid.uuid4(),
        )
        await TransferCRUD(self.session).create(transfer)

        # TODO: send email with URL for accepting(or declining)
        url = self._generate_transfer_url()

        # Send email to the user
        service: MailingService = MailingService()

        html_payload: dict = {
            "coordinator_name": f"{self._user.first_name} "
            "{self._user.last_name}",
            "user_name": transfer_request.email,
            "applet": applet.display_name,
            "role": "owner",
            "key": transfer.key,
            "email": transfer_request.email,
            "title": "Transfer ownership of an Applet",
            "body": None,
            "link": url,
        }
        try:
            await UsersCRUD(self.session).get_by_email(transfer_request.email)
        except UserNotFound:
            path = "invitation_new_user_en"
        else:
            path = "invitation_registered_user_en"

        message = MessageSchema(
            recipients=[transfer_request.email],
            subject="Transfer ownership of an Applet",
            body=service.get_template(path=path, **html_payload),
        )

        await service.send(message)

    async def accept_transfer(self, applet_id: uuid.UUID, key: uuid.UUID):
        """Respond to a transfer of ownership of an applet."""
        await AppletsCRUD(self.session).get_by_id(applet_id)
        transfer = await TransferCRUD(self.session).get_by_key(key=key)

        if (
            transfer.email != self._user.email
            or applet_id != transfer.applet_id
        ):
            raise PermissionsError()

        # delete all users from applet
        await UserAppletAccessCRUD(self.session).delete_all_by_applet_id(
            applet_id=transfer.applet_id
        )

        # add new owner to applet
        await UserAppletAccessCRUD(self.session).save(
            UserAppletAccessSchema(
                user_id=self._user.id,
                applet_id=transfer.applet_id,
                role=Role.ADMIN,
                owner_id=self._user.id,
                invitor_id=self._user.id,
                meta={},
            )
        )

        # delete responses from applet?
        await AnswerActivityItemsCRUD(self.session).delete_by_applet_user(
            applet_id=transfer.applet_id
        )
        await AnswerFlowItemsCRUD(self.session).delete_by_applet_user(
            applet_id=transfer.applet_id
        )

        # TODO: remove password from applet

        # delete all other transfers for this applet
        await TransferCRUD(self.session).delete_all_by_applet_id(
            applet_id=transfer.applet_id
        )

    def _generate_transfer_url(self) -> str:
        domain = settings.service.urls.frontend.web_base
        url_path = settings.service.urls.frontend.transfer_link
        return f"https://{domain}/{url_path}"

    async def decline_transfer(self, applet_id: uuid.UUID, key: uuid.UUID):
        """Decline a transfer of ownership of an applet."""
        await AppletsCRUD(self.session).get_by_id(applet_id)
        transfer = await TransferCRUD(self.session).get_by_key(key=key)

        if transfer.email != self._user.email:
            raise PermissionsError()

        # delete transfer
        await TransferCRUD(self.session).delete_by_key(key=key)
