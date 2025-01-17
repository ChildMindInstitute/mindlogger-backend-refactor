import uuid

from apps.applets.domain import UserAppletAccess
from apps.workspaces.crud.applet_access import AppletAccessCRUD

__all__ = ["AppletAccessService"]

from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.domain.constants import Role


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

    async def get_applet_accesses(self, user_id: uuid.UUID, applet_ids: list[uuid.UUID]) -> list[UserAppletAccess]:
        """
        Get a list of all a user's accesses for the specified applets
        :return:
        """
        crud = UserAppletAccessCRUD(self.session)
        schemas = await crud.get_user_applet_accesses_by_roles(user_id, applet_ids, Role.as_list())
        return [UserAppletAccess.from_orm(schema) for schema in schemas]
