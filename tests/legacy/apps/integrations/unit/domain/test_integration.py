import uuid

import pytest

from apps.integrations.domain import Integration


def test_integration_model():
    integration_data = {
        "integration_type": "LORIS",
        "applet_id": uuid.UUID("00000000-0000-0000-0000-000000000000"),
        "configuration": {"hostname": "hostname", "username": "user", "password": "password", "project": "project"},
    }
    item = Integration(**integration_data)
    assert item.integration_type == integration_data["integration_type"]


def test_integration_model_error():
    integration_data = {
        "integration_type": "MORRIS",
        "applet_id": uuid.UUID("00000000-0000-0000-0000-000000000000"),
        "configuration": {"hostname": "hostname", "username": "user", "password": "password", "project": "project"},
    }
    with pytest.raises(Exception):
        Integration(**integration_data)
