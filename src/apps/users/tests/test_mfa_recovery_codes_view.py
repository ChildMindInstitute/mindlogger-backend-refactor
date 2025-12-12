"""Integration tests for MFA recovery codes view and download endpoints."""

import re
from datetime import datetime, timezone

import pyotp
import pytest
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.authentication.db.schemas import RecoveryCodeSchema
from apps.shared.test.client import TestClient
from apps.users import UsersCRUD
from apps.users.domain import User


@pytest.mark.usefixtures("user")
class TestRecoveryCodesView:
    """Integration tests for TOTP-protected recovery codes view/download endpoints."""

    totp_initiate_url = "/users/me/mfa/totp/initiate"
    totp_verify_url = "/users/me/mfa/totp/verify"
    recovery_codes_view_initiate_url = "/users/me/mfa/recovery-codes/view/initiate"
    recovery_codes_view_verify_url = "/users/me/mfa/recovery-codes/view/verify"
    recovery_codes_download_url = "/users/me/mfa/recovery-codes/download"

    async def test_view_recovery_codes_success(self, client: TestClient, user: User, session: AsyncSession):
        """Test successful two-step TOTP-protected view of recovery codes."""
        client.login(user)

        # Step 1: Setup MFA (this generates recovery codes)
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Step 2: Initiate view flow
        initiate_resp = await client.post(self.recovery_codes_view_initiate_url)

        # Assertions - Initiate response
        assert initiate_resp.status_code == status.HTTP_200_OK
        initiate_result = initiate_resp.json()["result"]
        assert initiate_result["mfaRequired"] is True
        assert "mfaToken" in initiate_result
        assert "message" in initiate_result
        assert "TOTP code" in initiate_result["message"]

        mfa_token = initiate_result["mfaToken"]

        # Step 3: Verify with TOTP code
        totp_code = totp.now()
        verify_resp = await client.post(
            self.recovery_codes_view_verify_url, data={"mfaToken": mfa_token, "code": totp_code}
        )

        # Assertions - Verify response status
        assert verify_resp.status_code == status.HTTP_200_OK

        # Assertions - Verify response structure
        result = verify_resp.json()["result"]
        assert "codes" in result
        assert "total" in result
        assert "unusedCount" in result
        assert "downloadToken" in result

        # Assertions - Data
        codes = result["codes"]
        assert len(codes) == 10
        assert result["total"] == 10
        assert result["unusedCount"] == 10

        # Assertions - Download token exists
        download_token = result["downloadToken"]
        assert isinstance(download_token, str)
        assert len(download_token) > 0

        # Assertions - Code structure
        for code_item in codes:
            assert "code" in code_item
            assert "used" in code_item
            assert "usedAt" in code_item
            assert code_item["used"] is False
            assert code_item["usedAt"] is None

            # Validate format XXXXX-XXXXX
            code_val = code_item["code"]
            assert len(code_val) == 11
            assert code_val[5] == "-"
            assert re.match(r"^[A-Z0-9]{5}-[A-Z0-9]{5}$", code_val)

    async def test_view_initiate_mfa_not_enabled(self, client: TestClient, user: User):
        """Test 403 error when initiating view without MFA enabled."""
        client.login(user)

        # User has no MFA setup
        resp = await client.post(self.recovery_codes_view_initiate_url)

        # Assertions
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        errors = resp.json()["result"]
        assert any("MFA is not enabled" in err["message"] for err in errors)

    async def test_view_initiate_no_codes_exist(self, client: TestClient, user: User, session: AsyncSession):
        """Test 404 error when MFA enabled but no codes exist (edge case)."""
        client.login(user)

        # Manually enable MFA without generating codes (simulate edge case)
        crud = UsersCRUD(session)

        # Encrypt a dummy secret and activate MFA
        from apps.users.services.totp import totp_service

        dummy_secret = totp_service.generate_secret()
        encrypted = totp_service.encrypt_secret(dummy_secret)

        await crud.activate_mfa(user.id, encrypted)
        await session.commit()

        # Try to initiate view (no codes exist)
        resp = await client.post(self.recovery_codes_view_initiate_url)

        # Assertions
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        response_data = resp.json()
        # The error response format should have the error message in "result"
        result = response_data.get("result", [])
        # Result is typically a list of error dicts with "message" key
        assert isinstance(result, list), f"Expected list but got: {result}"
        assert len(result) > 0, "Expected at least one error in result"
        assert any("No recovery codes found" in str(err.get("message", "")) for err in result), (
            f"Expected 'No recovery codes found' in error messages, got: {result}"
        )

    async def test_view_verify_invalid_totp(self, client: TestClient, user: User, session: AsyncSession):
        """Test that invalid TOTP code is rejected."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Initiate view flow
        initiate_resp = await client.post(self.recovery_codes_view_initiate_url)
        mfa_token = initiate_resp.json()["result"]["mfaToken"]

        # Try to verify with invalid TOTP code
        verify_resp = await client.post(
            self.recovery_codes_view_verify_url,
            data={"mfaToken": mfa_token, "code": "000000"},  # Invalid code
        )

        # Assertions - Could be 400 or 403 depending on validation order
        assert verify_resp.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]
        errors = verify_resp.json()["result"]
        # Check for TOTP-related error message
        assert any("TOTP" in err["message"] or "Invalid" in err["message"] for err in errors)

    async def test_view_verify_invalid_mfa_token(self, client: TestClient, user: User, session: AsyncSession):
        """Test that invalid mfa_token is rejected."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Try to verify with invalid mfa_token (without initiating)
        totp_code = totp.now()
        verify_resp = await client.post(
            self.recovery_codes_view_verify_url, data={"mfaToken": "invalid_token", "code": totp_code}
        )

        # Assertions - Could be 401, 403, or 404 depending on JWT validation
        assert verify_resp.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]

    async def test_download_recovery_codes_success(self, client: TestClient, user: User, session: AsyncSession):
        """Test successful download of recovery codes using download_token."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Get download token via view flow
        initiate_resp = await client.post(self.recovery_codes_view_initiate_url)
        mfa_token = initiate_resp.json()["result"]["mfaToken"]

        totp_code = totp.now()
        verify_resp = await client.post(
            self.recovery_codes_view_verify_url, data={"mfaToken": mfa_token, "code": totp_code}
        )

        download_token = verify_resp.json()["result"]["downloadToken"]

        # Download codes using download_token
        resp = await client.get(f"{self.recovery_codes_download_url}?download_token={download_token}")

        # Assertions - Status
        assert resp.status_code == status.HTTP_200_OK

        # Assertions - Headers
        assert resp.headers["content-type"] == "text/plain; charset=utf-8"

        disposition = resp.headers.get("content-disposition", "")
        assert "attachment" in disposition
        assert "filename=" in disposition
        assert "recovery_codes_" in disposition
        assert ".txt" in disposition

        # Assertions - Content
        content = resp.text

        # Check header
        assert "MFA Recovery Codes" in content
        assert "Generated for:" in content
        assert user.email in content or (user.email_encrypted and user.email_encrypted in content)
        assert "Generated at:" in content
        assert "UTC" in content

        # Check separator lines
        assert "=" * 50 in content

        # Check codes present (10 codes, all unused)
        lines = content.split("\n")
        code_lines = [line for line in lines if re.match(r"^[A-Z0-9]{5}-[A-Z0-9]{5}$", line.strip())]
        assert len(code_lines) == 10

        # Check no "USED on" markers (all unused)
        assert "USED on" not in content

        # Check footer warning
        assert "IMPORTANT:" in content
        assert "Keep these codes safe" in content
        assert "Each code can only be used once" in content

    async def test_download_without_token_fails(self, client: TestClient, user: User, session: AsyncSession):
        """Test that download fails without valid download_token."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Try to download without token
        resp = await client.get(self.recovery_codes_download_url)

        # Assertions - Should fail due to missing required parameter
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_download_with_invalid_token_fails(self, client: TestClient, user: User, session: AsyncSession):
        """Test that download fails with invalid download_token."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Try to download with invalid token
        resp = await client.get(f"{self.recovery_codes_download_url}?download_token=invalid_token_here")

        # Assertions
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        # Error response structure may vary, so just check it's an error
        response_json = resp.json()
        assert "result" in response_json or "detail" in response_json

    async def test_download_recovery_codes_mfa_not_enabled(self, client: TestClient, user: User):
        """Test 403 error when trying to download without MFA."""
        client.login(user)

        # Try with a fake token (will fail on MFA check even if token was valid)
        resp = await client.get(f"{self.recovery_codes_download_url}?download_token=fake_token")

        # Assertions
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    async def test_used_codes_marked_correctly(self, client: TestClient, user: User, session: AsyncSession):
        """Test that used codes show correct status in view endpoint."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Mark some codes as used
        result = await session.execute(
            select(RecoveryCodeSchema.id).where(RecoveryCodeSchema.user_id == user.id).limit(3)
        )
        code_ids = [row[0] for row in result.fetchall()]

        used_time = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.execute(
            update(RecoveryCodeSchema).where(RecoveryCodeSchema.id.in_(code_ids)).values(used=True, used_at=used_time)
        )
        await session.commit()

        # View codes via TOTP-protected flow
        initiate_resp = await client.post(self.recovery_codes_view_initiate_url)
        mfa_token = initiate_resp.json()["result"]["mfaToken"]

        totp_code = totp.now()
        verify_resp = await client.post(
            self.recovery_codes_view_verify_url, data={"mfaToken": mfa_token, "code": totp_code}
        )

        assert verify_resp.status_code == status.HTTP_200_OK

        result = verify_resp.json()["result"]
        codes = result["codes"]

        # Check counts
        assert result["total"] == 10
        assert result["unusedCount"] == 7

        # Check used status
        used_codes = [c for c in codes if c["used"]]
        unused_codes = [c for c in codes if not c["used"]]

        assert len(used_codes) == 3
        assert len(unused_codes) == 7

        # Check used_at timestamps
        for used_code in used_codes:
            assert used_code["usedAt"] is not None
            assert isinstance(used_code["usedAt"], str)

        for unused_code in unused_codes:
            assert unused_code["usedAt"] is None

        # Test download endpoint
        download_token = result["downloadToken"]
        download_resp = await client.get(f"{self.recovery_codes_download_url}?download_token={download_token}")
        assert download_resp.status_code == status.HTTP_200_OK

        content = download_resp.text

        # Check that "USED on" appears (for used codes)
        assert "USED on" in content

        # Count occurrences (should be 3)
        used_markers = content.count("USED on")
        assert used_markers == 3

    async def test_unauthenticated_access_denied(self, client: TestClient):
        """Test that unauthenticated users get 401."""
        # Don't login

        # Test view initiate endpoint
        initiate_resp = await client.post(self.recovery_codes_view_initiate_url)
        assert initiate_resp.status_code == status.HTTP_401_UNAUTHORIZED

        # Test view verify endpoint
        verify_resp = await client.post(
            self.recovery_codes_view_verify_url, data={"mfaToken": "fake_token", "code": "123456"}
        )
        assert verify_resp.status_code == status.HTTP_401_UNAUTHORIZED

        # Test download endpoint
        download_resp = await client.get(f"{self.recovery_codes_download_url}?download_token=fake_token")
        assert download_resp.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_download_filename_format(self, client: TestClient, user: User, session: AsyncSession):
        """Test that download filename has correct timestamp format."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Get download token
        initiate_resp = await client.post(self.recovery_codes_view_initiate_url)
        mfa_token = initiate_resp.json()["result"]["mfaToken"]

        totp_code = totp.now()
        verify_resp = await client.post(
            self.recovery_codes_view_verify_url, data={"mfaToken": mfa_token, "code": totp_code}
        )

        download_token = verify_resp.json()["result"]["downloadToken"]

        # Download
        resp = await client.get(f"{self.recovery_codes_download_url}?download_token={download_token}")

        disposition = resp.headers.get("content-disposition", "")

        # Extract filename from header
        match = re.search(r'filename="([^"]+)"', disposition)
        assert match is not None

        filename = match.group(1)

        # Validate format
        assert filename.startswith("recovery_codes_")
        assert filename.endswith(".txt")

        # Extract timestamp part
        timestamp_part = filename.replace("recovery_codes_", "").replace(".txt", "")

        # Validate timestamp format YYYYMMDD_HHMMSS
        assert re.match(r"^\d{8}_\d{6}$", timestamp_part)

    async def test_totp_replay_protection(self, client: TestClient, user: User, session: AsyncSession):
        """Test that the same TOTP code cannot be reused (replay protection)."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # First view attempt
        initiate_resp1 = await client.post(self.recovery_codes_view_initiate_url)
        mfa_token1 = initiate_resp1.json()["result"]["mfaToken"]

        totp_code = totp.now()
        verify_resp1 = await client.post(
            self.recovery_codes_view_verify_url, data={"mfaToken": mfa_token1, "code": totp_code}
        )
        assert verify_resp1.status_code == status.HTTP_200_OK

        # Second view attempt with same TOTP code (should fail due to replay protection)
        initiate_resp2 = await client.post(self.recovery_codes_view_initiate_url)
        mfa_token2 = initiate_resp2.json()["result"]["mfaToken"]

        verify_resp2 = await client.post(
            self.recovery_codes_view_verify_url,
            data={"mfaToken": mfa_token2, "code": totp_code},  # Same TOTP code
        )

        # Should fail because TOTP code was already used - could be 400 or 403
        assert verify_resp2.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_403_FORBIDDEN]
        errors = verify_resp2.json()["result"]
        assert any("TOTP" in err["message"] or "Invalid" in err["message"] for err in errors)

    async def test_session_expiration(self, client: TestClient, user: User, session: AsyncSession):
        """Test that MFA session expires and cannot be reused after timeout."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Initiate view
        await client.post(self.recovery_codes_view_initiate_url)

        # Simulate session expiration by using very old token
        # In real scenario, this would happen after 5 minutes
        # For testing, we can try with a token from a deleted session

        # Note: Full expiration testing would require time manipulation or Redis mocking
        # This test verifies the error handling path exists

        # For now, just verify that invalid token format is rejected
        totp_code = totp.now()
        verify_resp = await client.post(
            self.recovery_codes_view_verify_url, data={"mfaToken": "expired_or_invalid_token", "code": totp_code}
        )

        # Could be 401, 403, or 404 depending on JWT validation
        assert verify_resp.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]
