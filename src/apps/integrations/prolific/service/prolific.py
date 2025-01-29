import uuid

import requests

from apps.integrations.crud.integrations import IntegrationsCRUD
from apps.integrations.db.schemas import IntegrationsSchema
from apps.integrations.domain import AvailableIntegrations
from apps.integrations.prolific.domain import ProlificIntegration
from apps.integrations.prolific.errors import ProlificInvalidApiTokenError
from apps.users.domain import User


class ProlificIntegrationService:
    def __init__(self, applet_id: uuid.UUID, session, user: User) -> None:
        self.applet_id = applet_id
        self.session = session
        self.user = user
        self.type = AvailableIntegrations.PROLIFIC

    async def create_prolific_integration(self, api_key: str) -> ProlificIntegration:
        prolific_response = requests.get(
            "https://api.prolific.com/api/v1/users/me/",
            headers={"Authorization": f"Token {api_key}", "Content-Type": "application/json"},
        )

        if prolific_response.status_code != 200:
            raise ProlificInvalidApiTokenError()

        integration_schema = await IntegrationsCRUD(self.session).create(
            IntegrationsSchema(
                applet_id=self.applet_id,
                type=self.type,
                configuration={
                    "api_key": api_key,
                },
            )
        )

        return ProlificIntegration.from_schema(integration_schema)
