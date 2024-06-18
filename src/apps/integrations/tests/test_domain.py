import pytest

from apps.integrations.domain import Integration


def test_integration_model():
    integration_data = {
        "integration_type": "LORIS",
    }
    item = Integration(**integration_data)
    assert item.integration_type == integration_data["integration_type"]


def test_integration_model_error():
    integration_data = {
        "integration_type": "MORRIS",
    }
    with pytest.raises(Exception):
        Integration(**integration_data)
