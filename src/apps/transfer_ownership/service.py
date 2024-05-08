import datetime
import uuid

from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.domain import Role
from apps.authentication.errors import PermissionsError
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.transfer_ownership.constants import TransferOwnershipStatus
from apps.transfer_ownership.crud import TransferCRUD
from apps.transfer_ownership.domain import InitiateTransfer, Transfer
from apps.transfer_ownership.errors import TransferEmailError
from apps.users import UsersCRUD
from apps.users.domain import User
from apps.workspaces.db.schemas import UserAppletAccessSchema
from config import settings


class TransferService:
    def __init__(self, session, user: User):
        self._user = user
        self.session = session

    async def initiate_transfer(self, applet_id: uuid.UUID, transfer_request: InitiateTransfer):
        """Initiate a transfer of ownership of an applet."""
        # check if user is owner of applet
        applet = await AppletsCRUD(self.session).get_by_id(id_=applet_id)

        to_user = await UsersCRUD(self.session).get_user_or_none_by_email(transfer_request.email)

        if to_user:
            if to_user.id == self._user.id:
                raise TransferEmailError()
            receiver_name = to_user.first_name
            path = "transfer_ownership_registered_user_en"
            to_user_id = to_user.id
        else:
            path = "transfer_ownership_unregistered_user_en"
            receiver_name = transfer_request.email
            to_user_id = None

        transfer = Transfer(
            email=transfer_request.email,
            applet_id=applet_id,
            key=uuid.uuid4(),
            status=TransferOwnershipStatus.PENDING,
            from_user_id=self._user.id,
            to_user_id=to_user_id,
        )
        await TransferCRUD(self.session).create(transfer)

        url = self._generate_transfer_url()

        service = MailingService()

        message = MessageSchema(
            recipients=[transfer_request.email],
            subject="Transfer ownership of an applet",
            body=service.get_template(
                path=path,
                applet_owner=self._user.get_full_name(),
                receiver_name=receiver_name,
                applet_name=applet.display_name,
                applet_id=applet.id,
                key=transfer.key,
                title="Transfer ownership of an Applet",
                link=url,
                current_year=datetime.date.today().year,
                url=self._generate_create_account_url(),
            ),
        )

        await service.send(message)

    async def accept_transfer(self, applet_id: uuid.UUID, key: uuid.UUID):
        """Respond to a transfer of ownership of an applet."""
        await AppletsCRUD(self.session).get_by_id(applet_id)
        transfer = await TransferCRUD(self.session).get_by_key(key=key)

        if transfer.email != self._user.email_encrypted or applet_id != transfer.applet_id:
            raise PermissionsError()

        # delete previous owner's accesses
        previous_owner = await UserAppletAccessCRUD(self.session).get_applet_owner(applet_id=applet_id)
        await UserAppletAccessCRUD(self.session).remove_access_by_user_and_applet_to_role(
            user_id=previous_owner.user_id,
            applet_ids=[
                applet_id,
            ],
            roles=[
                Role.OWNER,
            ],
        )

        await TransferCRUD(self.session).approve_by_key(key, self._user.id)
        await TransferCRUD(self.session).decline_all_pending_by_applet_id(applet_id=transfer.applet_id)

        # add new owner and respondent to applet
        roles_data = dict(
            user_id=self._user.id,
            applet_id=transfer.applet_id,
            owner_id=self._user.id,
            invitor_id=self._user.id,
            is_deleted=False,
        )

        roles_to_add = [
            UserAppletAccessSchema(role=Role.OWNER, meta={}, **roles_data),
            UserAppletAccessSchema(
                role=Role.RESPONDENT,
                meta=dict(
                    secretUserId=str(uuid.uuid4()),
                ),
                nickname=self._user.get_full_name(),
                **roles_data,
            ),
        ]
        await UserAppletAccessCRUD(self.session).upsert_user_applet_access_list(roles_to_add)

        # remove other roles of new owner
        await UserAppletAccessCRUD(self.session).remove_access_by_user_and_applet_to_role(
            user_id=self._user.id,
            applet_ids=[
                applet_id,
            ],
            roles=[
                Role.MANAGER,
                Role.COORDINATOR,
                Role.EDITOR,
                Role.REVIEWER,
            ],
        )

        # change other accesses' owner_id to current owner
        await UserAppletAccessCRUD(self.session).change_owner_of_applet_accesses(
            new_owner=self._user.id, applet_id=applet_id
        )

    def _generate_transfer_url(self) -> str:
        domain = settings.service.urls.frontend.web_base
        url_path = settings.service.urls.frontend.transfer_link
        return f"https://{domain}/{url_path}"

    def _generate_create_account_url(self) -> str:
        domain = settings.service.urls.frontend.admin_base
        url_path = settings.service.urls.frontend.create_account
        return f"https://{domain}/{url_path}"

    async def decline_transfer(self, applet_id: uuid.UUID, key: uuid.UUID):
        """Decline a transfer of ownership of an applet."""
        await AppletsCRUD(self.session).get_by_id(applet_id)
        transfer = await TransferCRUD(self.session).get_by_key(key=key)

        if transfer.email != self._user.email_encrypted or applet_id != transfer.applet_id:
            raise PermissionsError()

        # delete transfer
        await TransferCRUD(self.session).decline_by_key(key, self._user.id)
