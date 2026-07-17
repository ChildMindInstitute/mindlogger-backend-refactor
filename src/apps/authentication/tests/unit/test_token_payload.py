import uuid

import pytest
from pydantic import ValidationError

from apps.authentication.domain.token import TokenPayload
from infrastructure.http.domain import MindloggerContentSource


def payload_data(**kwargs) -> dict:
    return {
        "sub": str(uuid.uuid4()),
        "exp": 1893456000,
        "jti": str(uuid.uuid4()),
        **kwargs,
    }


def test_token_payload_without_client_claim():
    """Tokens issued before the client claim existed must still parse."""
    payload = TokenPayload(**payload_data())
    assert payload.client is None


@pytest.mark.parametrize("client", list(MindloggerContentSource))
def test_token_payload_with_client_claim(client: MindloggerContentSource):
    payload = TokenPayload(**payload_data(client=client.value))
    assert payload.client == client


def test_token_payload_with_unknown_client_value():
    with pytest.raises(ValidationError):
        TokenPayload(**payload_data(client="invalid-content-source"))
