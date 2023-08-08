import uuid

from apps.workspaces.crud.user_workspase_arbitrary import (
    UserWorkspaceArbitraryCRUD,
)
from apps.workspaces.domain.workspace import WorkspaceArbitrary


class WorkspaceArbitraryService:
    def __init__(self, session):
        self.session = session

    async def read_by_applet(
        self, applet_id: uuid.UUID
    ) -> WorkspaceArbitrary | None:
        schema = await UserWorkspaceArbitraryCRUD(self.session).get_by_applet(
            applet_id
        )
        return WorkspaceArbitrary.from_orm(schema) if schema else None
