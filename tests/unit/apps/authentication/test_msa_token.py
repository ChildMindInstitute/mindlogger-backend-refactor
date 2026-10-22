import uuid

import pytest

from apps.authentication.errors import MSATokenInvalidError
from apps.authentication.services.security import AuthenticationService


def test_msa_token_round_trip():
    user_id = uuid.uuid4()

    token = AuthenticationService.create_msa_token(user_id)

    assert AuthenticationService.validate_msa_token(token) == user_id


def test_msa_token_rejects_other_purpose():
    # Same signing key, different purpose: must not be usable to accept the MSA
    token = AuthenticationService.create_download_recovery_codes_token(uuid.uuid4())

    with pytest.raises(MSATokenInvalidError):
        AuthenticationService.validate_msa_token(token)
