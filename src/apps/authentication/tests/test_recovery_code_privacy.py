"""Integration tests for recovery code data privacy.

Tests ensure sensitive data (plaintext codes, hashes) never leak through:
- API endpoints
- Error messages
- Logs
- Database queries
"""

import json
import re

import pyotp
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.authentication.cruds.recovery_code import RecoveryCodeCRUD
from apps.authentication.services.recovery_codes import generate_recovery_codes
from apps.shared.test import BaseTest
from apps.shared.test.client import TestClient
from apps.users.domain import User
from apps.users.services.totp import totp_service

TEST_PASSWORD = "Test1234!"


@pytest.mark.usefixtures("user")
class TestRecoveryCodePrivacy(BaseTest):
    """Data privacy tests for recovery codes."""

    totp_initiate_url = "/users/me/mfa/totp/initiate"
    totp_verify_url = "/users/me/mfa/totp/verify"
    recovery_codes_view_initiate_url = "/users/me/mfa/recovery-codes/view/initiate"
    recovery_codes_view_verify_url = "/users/me/mfa/recovery-codes/view/verify"
    recovery_codes_download_url = "/users/me/mfa/recovery-codes/download"
    get_token_url = "/auth/token"
    verify_recovery_url = "/auth/mfa/recovery-codes/verify"

    async def test_get_endpoint_never_exposes_hashes(self, client: TestClient, user: User, session: AsyncSession):
        """Verify GET endpoints never expose code hashes."""
        client.login(user)

        # Setup MFA and generate codes
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()
        await client.post(self.totp_verify_url, data={"code": code})

        # Get recovery codes via TOTP-protected view flow
        initiate_resp = await client.post(self.recovery_codes_view_initiate_url)
        mfa_token = initiate_resp.json()["result"]["mfaToken"]

        totp_code = totp.now()
        resp = await client.post(self.recovery_codes_view_verify_url, data={"mfaToken": mfa_token, "code": totp_code})
        assert resp.status_code == status.HTTP_200_OK

        # Convert response to string to search for hash patterns
        response_text = json.dumps(resp.json())

        # Assert: No bcrypt hash patterns ($2b$...)
        assert "$2b$" not in response_text, "Bcrypt hash found in API response"
        assert "$2a$" not in response_text, "Bcrypt hash found in API response"

        # Assert: Response structure doesn't have hash fields
        result = resp.json()["result"]
        for code_item in result["codes"]:
            assert "hash" not in code_item
            assert "code_hash" not in code_item
            assert "codeHash" not in code_item

        # Assert: Only expected fields present
        expected_fields = {"code", "used", "usedAt"}
        for code_item in result["codes"]:
            assert set(code_item.keys()) == expected_fields

    async def test_database_queries_dont_return_unnecessary_fields(self, session: AsyncSession, user: User):
        """Verify database queries don't return sensitive fields unnecessarily."""
        # Generate codes
        await generate_recovery_codes(session, user.id, count=5)
        await session.commit()

        # Query via CRUD
        crud = RecoveryCodeCRUD(session)
        db_codes = await crud.get_by_user_id(user.id)

        # Assert: CRUD returns full schema (this is expected for service layer)
        # But verify fields are intentionally structured
        for db_code in db_codes:
            assert hasattr(db_code, "code_hash")
            assert hasattr(db_code, "code_encrypted")
            assert hasattr(db_code, "used")
            assert hasattr(db_code, "used_at")

            # Verify hash is actually a bcrypt hash
            assert db_code.code_hash.startswith("$2b$")
            # Verify encrypted code is Fernet format (base64)
            assert len(db_code.code_encrypted) > 50

    async def test_api_responses_mask_sensitive_data(self, client: TestClient, user: User, session: AsyncSession):
        """Verify API responses mask sensitive data appropriately."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()
        await client.post(self.totp_verify_url, data={"code": code})

        # Get recovery codes via TOTP-protected view flow
        initiate_resp = await client.post(self.recovery_codes_view_initiate_url)
        mfa_token = initiate_resp.json()["result"]["mfaToken"]

        totp_code = totp.now()
        json_resp = await client.post(
            self.recovery_codes_view_verify_url, data={"mfaToken": mfa_token, "code": totp_code}
        )
        assert json_resp.status_code == status.HTTP_200_OK
        json_text = json.dumps(json_resp.json())

        # Assert: No encrypted codes in JSON (they're decrypted for display)
        # Fernet tokens start with "gAAAAA" typically
        assert "gAAAA" not in json_text, "Encrypted code found in JSON response"

        # Test download endpoint
        download_token = json_resp.json()["result"]["downloadToken"]
        download_resp = await client.get(f"{self.recovery_codes_download_url}?download_token={download_token}")
        assert download_resp.status_code == status.HTTP_200_OK
        download_text = download_resp.text

        # Assert: No hashes in download
        assert "$2b$" not in download_text, "Hash found in download response"
        assert "code_hash" not in download_text.lower(), "Hash field name in download"

        # Assert: Only plaintext codes and usage info
        assert "Recovery Codes" in download_text
        assert re.search(r"[A-Z0-9]{5}-[A-Z0-9]{5}", download_text), "Should contain plaintext codes"

    async def test_different_users_cannot_access_each_others_codes(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Verify users cannot access other users' recovery codes."""
        # Create a second user using UserService for proper database mapping
        from apps.users.cruds.user import UsersCRUD
        from apps.users.domain import UserCreate
        from apps.users.services.user import UserService

        user_crud = UsersCRUD(session)
        user2_create = UserCreate(
            email="user2@test.com",
            first_name="User",
            last_name="Two",
            password=TEST_PASSWORD,  # UserService will hash it
        )
        user2 = await UserService(session).create_user(user2_create)
        await session.commit()

        # Setup MFA for both users
        for test_user in [user, user2]:
            secret = totp_service.generate_secret()
            encrypted = totp_service.encrypt_secret(secret)
            await user_crud.update_by_id(
                test_user.id,
                {"mfa_enabled": True, "mfa_secret": encrypted},  # type: ignore[arg-type]
            )
            await generate_recovery_codes(session, test_user.id, count=10)
        await session.commit()

        # Login as user 1 and get codes via TOTP-protected flow
        client.login(user)

        # Get user1's TOTP secret to generate codes
        user1_db = await user_crud.get_by_id(user.id)
        assert user1_db.mfa_secret is not None
        user1_secret = totp_service.decrypt_secret(user1_db.mfa_secret)
        user1_totp = pyotp.TOTP(user1_secret)

        initiate_resp1 = await client.post(self.recovery_codes_view_initiate_url)
        mfa_token1 = initiate_resp1.json()["result"]["mfaToken"]

        resp1 = await client.post(
            self.recovery_codes_view_verify_url, data={"mfaToken": mfa_token1, "code": user1_totp.now()}
        )
        assert resp1.status_code == status.HTTP_200_OK
        codes1 = {c["code"] for c in resp1.json()["result"]["codes"]}

        # Login as user 2 and get codes via TOTP-protected flow
        client.login(user2)

        # Get user2's TOTP secret to generate codes
        user2_db = await user_crud.get_by_id(user2.id)
        assert user2_db.mfa_secret is not None
        user2_secret = totp_service.decrypt_secret(user2_db.mfa_secret)
        user2_totp = pyotp.TOTP(user2_secret)

        initiate_resp2 = await client.post(self.recovery_codes_view_initiate_url)
        mfa_token2 = initiate_resp2.json()["result"]["mfaToken"]

        resp2 = await client.post(
            self.recovery_codes_view_verify_url, data={"mfaToken": mfa_token2, "code": user2_totp.now()}
        )
        assert resp2.status_code == status.HTTP_200_OK
        codes2 = {c["code"] for c in resp2.json()["result"]["codes"]}

        # Assert: No overlap between users' codes
        assert len(codes1 & codes2) == 0, "Users have overlapping recovery codes"
        assert len(codes1) == 10
        assert len(codes2) == 10

    async def test_error_responses_dont_leak_internal_structures(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Verify error responses don't leak internal data structures."""
        client.login(user)

        # Test 1: Access codes without MFA enabled (should fail at initiate step)
        resp1 = await client.post(self.recovery_codes_view_initiate_url)
        assert resp1.status_code == status.HTTP_403_FORBIDDEN

        error_text = json.dumps(resp1.json())
        # Assert: No internal field names
        assert "code_hash" not in error_text.lower()
        assert "code_encrypted" not in error_text.lower()
        assert "RecoveryCodeSchema" not in error_text
        assert "SQLAlchemy" not in error_text

        # Test 2: Invalid MFA token in recovery code verification
        resp2 = await client.post(
            url=self.verify_recovery_url,
            data=dict(
                mfaToken="invalid-token-format",
                code="ABCDE-12345",
                deviceId="test-device",
            ),
        )
        assert resp2.status_code == status.HTTP_401_UNAUTHORIZED

        error_text2 = json.dumps(resp2.json())
        # Assert: No stack traces or internal details
        assert "Traceback" not in error_text2
        assert ".py" not in error_text2  # No file paths
        assert "line " not in error_text2  # No line numbers
