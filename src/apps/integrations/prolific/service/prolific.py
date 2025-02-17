import json
import uuid

import requests
from pydantic import ValidationError

from apps.applets.service.applet import AppletService
from apps.integrations.crud.integrations import IntegrationsCRUD
from apps.integrations.db.schemas import IntegrationsSchema
from apps.integrations.domain import AvailableIntegrations
from apps.integrations.prolific.domain import (
    ProlificCompletionCodeList,
    ProlificIntegration,
    ProlificStudyValidation,
)
from apps.integrations.prolific.errors import (
    ProlificIntegrationNotConfiguredError,
    ProlificInvalidApiTokenError,
    ProlificInvalidStudyError,
)

API_BASE_URL = "https://api.prolific.com/api/v1"
BASE_HEADERS = {"Content-Type": "application/json"}


class ProlificIntegrationService:
    def __init__(self, applet_id: uuid.UUID, session) -> None:
        self.applet_id = applet_id
        self.session = session
        self.type = AvailableIntegrations.PROLIFIC

    async def create_prolific_integration(self, api_key: str) -> ProlificIntegration:
        prolific_response = requests.get(
            f"{API_BASE_URL}/users/me/",
            headers={**BASE_HEADERS, "Authorization": f"Token {api_key}"},
        )

        if prolific_response.status_code != 200:
            raise ProlificInvalidApiTokenError()

        integration_schema = await IntegrationsCRUD(self.session).create(
            IntegrationsSchema(
                applet_id=self.applet_id,
                type=self.type,
                configuration=ProlificIntegration(api_key=api_key).json(),
            )
        )

        return ProlificIntegration.from_schema(integration_schema)

    async def validate_prolific_study(self, study_id, language, is_private_applet_id=False) -> ProlificStudyValidation:
        applet_service = AppletService(self.session, uuid.UUID("00000000-0000-0000-0000-000000000000"))
        applet_base_info = None
        if not is_private_applet_id:
            await applet_service.exist_by_key(self.applet_id)
            applet_base_info = await applet_service.get_info_by_key(self.applet_id, language)
            self.applet_id = applet_base_info.id  # Update the public applet key to be the real applet id
        else:
            await applet_service.exist_by_id(self.applet_id)
            applet_base_info = await applet_service.get_info_by_id(self.applet_id, language)

        api_key = await self._get_prolific_api_key()

        if not api_key:
            return ProlificStudyValidation(accepted=False)

        prolific_response = requests.get(
            f"{API_BASE_URL}/studies/{study_id}/", headers={**BASE_HEADERS, "Authorization": f"Token {api_key}"}
        )

        return ProlificStudyValidation(accepted=(prolific_response.status_code == 200))

    async def get_completion_codes(self, study_id: str) -> ProlificCompletionCodeList:
        api_key = await self._get_prolific_api_key()

        prolific_response = requests.get(
            f"{API_BASE_URL}/studies/{study_id}/", headers={**BASE_HEADERS, "Authorization": f"Token {api_key}"}
        )

        if prolific_response.status_code != 200:
            raise ProlificInvalidStudyError(message=prolific_response.text)

        return ProlificCompletionCodeList(completion_codes=prolific_response.json()["completion_codes"])

    async def _get_prolific_api_key(self) -> str | None:
        integration = await IntegrationsCRUD(self.session).retrieve_by_applet_and_type(
            applet_id=self.applet_id, integration_type=self.type
        )

        if not integration:
            return None

        try:
            return ProlificIntegration(**json.loads(integration.configuration)).api_key
        except ValidationError:
            raise ProlificIntegrationNotConfiguredError()
