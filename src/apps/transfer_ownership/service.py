import uuid

from apps.applets.crud import AppletsCRUD
from apps.authentication.errors import PermissionsError
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.transfer_ownership.crud import TransferCRUD
from apps.transfer_ownership.domain import (
    InitiateTransfer,
    Transfer,
    TransferResponse,
)
from apps.users.domain import User
from config import settings


class TransferService:
    def __init__(self, user: User):
        self._user = user

    async def initiate_transfer(
        self, applet_id: int, transfer_request: InitiateTransfer
    ):
        """Initiate a transfer of ownership of an applet."""
        # check if user is owner of applet
        applet = await AppletsCRUD().get_by_id(id_=applet_id)
        if applet.account_id != self._user.id:
            raise PermissionsError()

        transfer = Transfer(
            email=transfer_request.email,
            applet_id=applet_id,
            key=uuid.uuid4(),
        )
        await TransferCRUD().create(transfer)

        # TODO: send email with URL for accepting(or declining)
        url = self._generate_transfer_url(transfer.key)

        # Send email to the user
        service: MailingService = MailingService()

        html_payload: dict = {
            "coordinator_name": self._user.full_name,
            "user_name": transfer_request.email,
            "applet": applet.display_name,
            "role": "owner",
            "key": transfer.key,
            "email": transfer_request.email,
            "title": "Transfer ownership of an Applet",
            "body": None,
            "link": url,
        }
        message = MessageSchema(
            recipients=[transfer_request.email],
            subject="Transfer ownership of an Applet",
            body=service.get_template(path="invitation", **html_payload),
        )

        await service.send(message)

    async def respond_transfer(
        self, applet_id: int, key: uuid.UUID, response: TransferResponse
    ):
        """Respond to a transfer of ownership of an applet."""
        transfer = await TransferCRUD().get_by_key(key=key)

        if transfer.email != self._user.email:
            raise PermissionsError()

        if response.accepted:
            await AppletsCRUD().transfer_ownership(
                applet_id=transfer.applet_id,
                new_owner_id=self._user.id,
            )
            # delete all other transfers for this applet
            await TransferCRUD().delete_all_by_applet_id(
                applet_id=transfer.applet_id
            )
        else:
            # delete this transfer
            await TransferCRUD().delete_by_key(key=key)

    def _generate_transfer_url(self, key: uuid.UUID) -> str:
        domain = settings.service.urls.frontend.web_base
        url_path = settings.service.urls.frontend.transfer_link
        return f"https://{domain}/{url_path}"
