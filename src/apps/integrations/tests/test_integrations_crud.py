import uuid
from unittest.mock import AsyncMock

import pytest

from apps.integrations.crud import IntegrationsCRUD
from apps.integrations.db.schemas import IntegrationsSchema
from apps.integrations.domain import AvailableIntegrations


@pytest.fixture
def configuration():
    return '{"hostname":"url", "username":"david", "password":"abc"}'


@pytest.fixture
def integrations_data(uuid_zero: uuid.UUID, configuration: str):
    return {"applet_id": uuid_zero, "type": AvailableIntegrations.LORIS, "configuration": configuration}


@pytest.fixture
def integrations_schema(integrations_data):
    return IntegrationsSchema(**integrations_data)


@pytest.fixture
async def crud(session):
    return IntegrationsCRUD(session)


@pytest.mark.asyncio
async def test_create(crud, integrations_schema, mocker):
    mock_create = mocker.patch.object(crud, "_create", return_value=AsyncMock())
    mock_create.return_value = integrations_schema

    result = await crud.create(integrations_schema)

    assert result == integrations_schema
    mock_create.assert_called_once_with(integrations_schema)
