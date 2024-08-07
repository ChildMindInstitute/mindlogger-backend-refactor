from apps.integrations.domain import AvailableIntegrations, Integration
from apps.integrations.errors import UniqueIntegrationError
from apps.shared.query_params import QueryParams
from apps.users.domain import User
from apps.workspaces.crud.workspaces import UserWorkspaceCRUD

__all__ = [
    "IntegrationService",
]


class IntegrationService:
    def __init__(self, session, user: User) -> None:
        self.session = session
        self.user = user

    async def enable_integration(self, integrations: list[Integration]):
        workspace = await UserWorkspaceCRUD(self.session).get_by_user_id(user_id_=self.user.id)
        integration_names: list[AvailableIntegrations] = [integration.integration_type for integration in integrations]
        if len(set(integration_names)) != len(integration_names):
            raise UniqueIntegrationError()

        workspace.integrations = [integration.dict() for integration in integrations]
        workspace = await UserWorkspaceCRUD(self.session).save(workspace)
        return [Integration.parse_obj(integration) for integration in workspace.integrations]

    async def disable_integration(self, query: QueryParams):
        workspace = await UserWorkspaceCRUD(self.session).get_by_user_id(user_id_=self.user.id)
        if query.filters:
            workspace.integrations = (
                [
                    integration
                    for integration in workspace.integrations
                    if integration["integration_type"] not in query.filters["integration_types"]
                ]
                if workspace.integrations
                else workspace.integrations
            )
        else:
            workspace.integrations = None
        await UserWorkspaceCRUD(self.session).save(workspace)
