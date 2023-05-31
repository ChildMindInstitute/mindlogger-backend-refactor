import datetime
import uuid

from apps.answers.crud.answers import AnswersCRUD
from apps.applets.crud import AppletsCRUD, UserAppletAccessCRUD
from apps.applets.domain import Role
from apps.authentication.errors import PermissionsError
from apps.invitations.services import InvitationsService
from apps.mailing.domain import MessageSchema
from apps.mailing.services import MailingService
from apps.transfer_ownership.crud import TransferCRUD
from apps.transfer_ownership.domain import InitiateTransfer, Transfer
from apps.transfer_ownership.errors import TransferEmailError
from apps.users import UserNotFound, UsersCRUD
from apps.users.domain import User
from apps.workspaces.db.schemas import UserAppletAccessSchema
from config import settings


class LibraryService:
    def __init__(self, session, user: User):
        self._user = user
        self.session = session

    async def share_applet(self, applet_id: uuid.UUID):
        """Share applet to library."""
        # check if user is owner of applet
        applet = await AppletsCRUD(self.session).get_by_id(id_=applet_id)

        # temporary solution
        access = await UserAppletAccessCRUD(self.session).get_applet_owner(
            applet_id
        )
        if access.user_id != self._user.id:
            raise PermissionsError()

        return True
