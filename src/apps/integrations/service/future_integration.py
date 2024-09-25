import uuid

from apps.integrations.crud.integrations import IntegrationsCRUD, IntegrationsSchema
from apps.integrations.domain import AvailableIntegrations, FutureIntegration, FutureIntegrationPublic


class FutureIntegrationService:
    """Template for future MindLogger integrations.

    This is an example of an integration that can be used
    as a template in the Future for other MindLogger integrations.

    Attributes:
        applet_id: A uuid.UUID that identifies the applet tied to the integration.
        session: A database session.
        type: An AvailableIntegrations enum that identifies the integration type.
    """

    def __init__(self, applet_id: uuid.UUID, session) -> None:
        self.applet_id = applet_id
        self.session = session
        self.type = AvailableIntegrations.FUTURE

    async def create_future_integration(self, endpoint) -> FutureIntegration:
        integration_schema = await IntegrationsCRUD(self.session).create(
            IntegrationsSchema(
                applet_id=self.applet_id,
                type=self.type,
                configuration={
                    "endpoint": endpoint,
                },
            )
        )
        return FutureIntegrationPublic.from_schema(integration_schema)
