import uuid

from apps.applets.domain import UserAppletAccess
from apps.workspaces.crud.applet_access import AppletAccessCRUD

__all__ = ["AppletAccessService"]


class AppletAccessService:
    def __init__(self, session):
        self.session = session

    async def get_priority_access(self, applet_id: uuid.UUID, user_id: uuid.UUID) -> UserAppletAccess | None:
        """
        Get the user's access to an applet with the most permissions. Returns accesses in this order:
        1. Owner
        2. Manager
        3. Coordinator
        4. Editor
        5. Reviewer
        6. Respondent
        :param applet_id:
        :param user_id:
        :return:
        """
        schema = await AppletAccessCRUD(self.session).get_priority_access(applet_id, user_id)
        if not schema:
            return None

        return UserAppletAccess.from_orm(schema)
