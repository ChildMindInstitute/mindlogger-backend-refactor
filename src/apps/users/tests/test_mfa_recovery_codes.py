"""Integration tests for MFA recovery codes generation during TOTP setup."""

import re

import pyotp
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.authentication.cruds import RecoveryCodeCRUD
from apps.shared.test.client import TestClient
from apps.users import UsersCRUD
from apps.users.db.schemas import UserSchema
from apps.users.domain import User


@pytest.mark.usefixtures("user")
class TestMFARecoveryCodes:
    """Integration tests for recovery code generation during MFA setup."""

    totp_initiate_url = "/users/me/mfa/totp/initiate"
    totp_verify_url = "/users/me/mfa/totp/verify"

    async def test_first_time_setup_generates_recovery_codes(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Test that first-time MFA setup returns 10 recovery codes."""
        client.login(user)

        # Step 1: Initiate TOTP setup
        init_resp = await client.post(self.totp_initiate_url)
        assert init_resp.status_code == status.HTTP_200_OK

        # Extract secret from provisioning URI
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        # Generate valid TOTP code
        totp = pyotp.TOTP(secret)
        code = totp.now()

        # Step 2: Verify TOTP code (first-time setup)
        verify_resp = await client.post(self.totp_verify_url, data={"code": code})

        assert verify_resp.status_code == status.HTTP_200_OK
        result = verify_resp.json()["result"]

        # Assertions
        assert result["mfaEnabled"] is True
        assert "recoveryCodes" in result
        assert result["recoveryCodes"] is not None
        assert isinstance(result["recoveryCodes"], list)
        assert len(result["recoveryCodes"]) == 10

    async def test_recovery_codes_stored_in_database(self, client: TestClient, user: User, session: AsyncSession):
        """Test that recovery codes are stored in database after generation."""
        client.login(user)

        # Setup and verify
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        verify_resp = await client.post(self.totp_verify_url, data={"code": code})
        assert verify_resp.status_code == status.HTTP_200_OK

        # Query database
        crud = RecoveryCodeCRUD(session)
        db_codes = await crud.get_by_user_id(user.id)

        # Assertions
        assert len(db_codes) == 10
        assert all(not code.used for code in db_codes)
        assert all(code.user_id == user.id for code in db_codes)
        assert all(code.code_hash is not None for code in db_codes)
        assert all(code.code_encrypted is not None for code in db_codes)

    async def test_user_timestamp_set_after_generation(self, client: TestClient, user: User, session: AsyncSession):
        """Test that user.recovery_codes_generated_at is set after generation."""
        client.login(user)

        # Verify initial state
        crud = UsersCRUD(session)
        initial_user = await crud.get_by_id(user.id)
        assert initial_user.recovery_codes_generated_at is None

        # Setup and verify
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Check updated user
        updated_user = await crud.get_by_id(user.id)

        # Assertions
        assert updated_user.recovery_codes_generated_at is not None
        assert updated_user.mfa_enabled is True

    async def test_reenrollment_no_codes_returned(self, client: TestClient, user: User, session: AsyncSession):
        """Test that re-enrollment does not regenerate recovery codes."""
        client.login(user)

        # First-time setup
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        first_resp = await client.post(self.totp_verify_url, data={"code": code})
        assert first_resp.status_code == status.HTTP_200_OK

        # Get timestamp and DB codes
        crud_user = UsersCRUD(session)
        user_after_first = await crud_user.get_by_id(user.id)
        first_timestamp = user_after_first.recovery_codes_generated_at

        crud_codes = RecoveryCodeCRUD(session)
        first_db_codes = await crud_codes.get_by_user_id(user.id)

        # Simulate re-enrollment (disable and re-enable MFA)
        await crud_user.update_by_id(user.id, UserSchema(mfa_enabled=False, mfa_secret=None))
        await session.commit()

        # Re-enroll
        reinit_resp = await client.post(self.totp_initiate_url)
        reuri = reinit_resp.json()["result"]["provisioningUri"]
        resecret = reuri.split("secret=")[1].split("&")[0]

        retotp = pyotp.TOTP(resecret)
        recode = retotp.now()

        second_resp = await client.post(self.totp_verify_url, data={"code": recode})

        # Assertions
        result = second_resp.json()["result"]
        assert result["mfaEnabled"] is True
        assert result["recoveryCodes"] is None  # No codes returned

        # Check timestamp unchanged
        user_after_second = await crud_user.get_by_id(user.id)
        assert user_after_second.recovery_codes_generated_at == first_timestamp

        # Check DB codes unchanged
        second_db_codes = await crud_codes.get_by_user_id(user.id)
        assert len(second_db_codes) == 10  # Still 10 codes
        assert len(first_db_codes) == len(second_db_codes)

    async def test_recovery_codes_format(self, client: TestClient, user: User, session: AsyncSession):
        """Test that returned recovery codes have correct format (XXXXX-XXXXX)."""
        client.login(user)

        # Setup and verify
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        verify_resp = await client.post(self.totp_verify_url, data={"code": code})
        codes = verify_resp.json()["result"]["recoveryCodes"]

        # Format validation
        pattern = r"^[A-Z0-9]{5}-[A-Z0-9]{5}$"

        for c in codes:
            assert isinstance(c, str)
            assert len(c) == 11  # 5 + hyphen + 5
            assert c[5] == "-"
            assert re.match(pattern, c), f"Code {c} doesn't match pattern"

        # Uniqueness check
        assert len(codes) == len(set(codes)), "Codes must be unique"
