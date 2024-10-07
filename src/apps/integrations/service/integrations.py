
from apps.integrations.crud.integrations import IntegrationsCRUD
from apps.integrations.domain import AvailableIntegrations, FutureIntegrationPublic, Integration
from apps.integrations.errors import (
    UnavailableIntegrationError,
    UnexpectedPropertiesForIntegration,
    UniqueIntegrationError,
    UnsupportedIntegrationError,
)
from apps.integrations.loris.domain.loris_integrations import LorisIntegrationPublic
from apps.integrations.loris.service.loris import LorisIntegrationService
from apps.integrations.service.future_integration import FutureIntegrationService
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

    async def create_integration(self, newIntegration: Integration) -> Integration:
        match newIntegration.integration_type:
            case AvailableIntegrations.LORIS:
                expected_keys = ["hostname", "username", "project", "password"]
                if None in [newIntegration.configuration.get(k, None) for k in expected_keys]:
                    raise UnexpectedPropertiesForIntegration(
                        provided_keys=list(newIntegration.configuration.keys()),
                        expected_keys=expected_keys,
                        integration_type=AvailableIntegrations.LORIS,
                    )
                loris_integration = await LorisIntegrationService(
                    newIntegration.applet_id, self.session, self.user
                ).create_loris_integration(
                    hostname=newIntegration.configuration["hostname"],
                    username=newIntegration.configuration["username"],
                    project=newIntegration.configuration["project"],
                    password=newIntegration.configuration["password"],
                )
                return Integration(
                    integration_type=AvailableIntegrations.LORIS,
                    applet_id=newIntegration.applet_id,
                    configuration=loris_integration,
                )
            case AvailableIntegrations.FUTURE:
                expected_keys = ["endpoint", "api_key"]
                if None in [newIntegration.configuration.get(k, None) for k in expected_keys]:
                    raise UnexpectedPropertiesForIntegration(
                        provided_keys=list(newIntegration.configuration.keys()),
                        expected_keys=expected_keys,
                        integration_type=AvailableIntegrations.FUTURE,
                    )
                future_integration = await FutureIntegrationService(
                    newIntegration.applet_id,
                    self.session,
                ).create_future_integration(
                    endpoint=newIntegration.configuration["endpoint"],
                    api_key=newIntegration.configuration["api_key"],
                )
                return Integration(
                    integration_type=AvailableIntegrations.FUTURE,
                    applet_id=newIntegration.applet_id,
                    configuration=future_integration,
                )
            case _:
                raise UnsupportedIntegrationError(integration_type=newIntegration.integration_type)

    async def retrieve_integration(self, applet_id, integration_type) -> Integration:
        integration_schema = await IntegrationsCRUD(self.session).retrieve_by_applet_and_type(
            applet_id,
            integration_type
        )

        if integration_schema is None:
            raise UnavailableIntegrationError(applet_id=applet_id, integration_type=integration_type)

        match integration_type:
            case AvailableIntegrations.LORIS:
                loris_integration = LorisIntegrationPublic.from_schema(integration_schema)
                return Integration(
                    integration_type=AvailableIntegrations.LORIS,
                    applet_id=applet_id,
                    configuration=loris_integration,
                )
            case AvailableIntegrations.FUTURE:
                future_integration = FutureIntegrationPublic.from_schema(integration_schema)
                return Integration(
                    integration_type=AvailableIntegrations.FUTURE,
                    applet_id=applet_id,
                    configuration=future_integration,
                )
            case _:
                raise UnsupportedIntegrationError(integration_type=integration_type)

    async def delete_integration_by_type(self, applet_id, integration_type):
        integration = await IntegrationsCRUD(self.session).retrieve_by_applet_and_type(
            applet_id,
            integration_type
        )
        if integration is not None:
            await IntegrationsCRUD(self.session).delete_by_id(integration.id)
        else:
            raise UnavailableIntegrationError(applet_id=applet_id, integration_type=integration_type)
