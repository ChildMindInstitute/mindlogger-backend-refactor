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
    """Integration tests for recovery codes view/download endpoints."""

    totp_initiate_url = "/users/me/mfa/totp/initiate"
    totp_verify_url = "/users/me/mfa/totp/verify"
    recovery_codes_url = "/users/me/mfa/recovery-codes"
    recovery_codes_download_url = "/users/me/mfa/recovery-codes/download"

    async def test_get_recovery_codes_success(self, client: TestClient, user: User, session: AsyncSession):
        """Test successful retrieval of recovery codes via JSON endpoint."""
        client.login(user)

        # Step 1: Setup MFA (this generates recovery codes)
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Step 2: Get recovery codes
        resp = await client.get(self.recovery_codes_url)

        # Assertions - Status
        assert resp.status_code == status.HTTP_200_OK

        # Assertions - Structure
        result = resp.json()["result"]
        assert "codes" in result
        assert "total" in result
        assert "unusedCount" in result

        # Assertions - Data
        codes = result["codes"]
        assert len(codes) == 10
        assert result["total"] == 10
        assert result["unusedCount"] == 10

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

    async def test_get_recovery_codes_mfa_not_enabled(self, client: TestClient, user: User):
        """Test 403 error when MFA is not enabled."""
        client.login(user)

        # User has no MFA setup
        resp = await client.get(self.recovery_codes_url)

        # Assertions
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        errors = resp.json()["result"]
        assert any("MFA is not enabled" in err["message"] for err in errors)

    async def test_get_recovery_codes_not_generated(self, client: TestClient, user: User, session: AsyncSession):
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

        # Try to get codes (none exist)
        resp = await client.get(self.recovery_codes_url)

        # Assertions
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        errors = resp.json()["result"]
        assert any("No recovery codes found" in err["message"] for err in errors)

    async def test_download_recovery_codes_success(self, client: TestClient, user: User, session: AsyncSession):
        """Test successful download of recovery codes as text file."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Download codes
        resp = await client.get(self.recovery_codes_download_url)

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

    async def test_download_recovery_codes_mfa_not_enabled(self, client: TestClient, user: User):
        """Test 403 error when trying to download without MFA."""
        client.login(user)

        resp = await client.get(self.recovery_codes_download_url)

        # Assertions
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    async def test_used_codes_marked_correctly(self, client: TestClient, user: User, session: AsyncSession):
        """Test that used codes show correct status in both endpoints."""
        client.login(user)

        # Setup MFA
        init_resp = await client.post(self.totp_initiate_url)
        uri = init_resp.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]

        totp = pyotp.TOTP(secret)
        code = totp.now()

        await client.post(self.totp_verify_url, data={"code": code})

        # Mark some codes as used by executing SQL directly
        # Note: We use SQL because the CRUD returns domain objects which we can't easily modify

        # Get the recovery code IDs to update
        result = await session.execute(
            select(RecoveryCodeSchema.id).where(RecoveryCodeSchema.user_id == user.id).limit(3)
        )
        code_ids = [row[0] for row in result.fetchall()]

        # Update the first 3 codes
        used_time = datetime.now(timezone.utc).replace(tzinfo=None)
        await session.execute(
            update(RecoveryCodeSchema).where(RecoveryCodeSchema.id.in_(code_ids)).values(used=True, used_at=used_time)
        )
        await session.commit()

        # Test JSON endpoint
        json_resp = await client.get(self.recovery_codes_url)
        assert json_resp.status_code == status.HTTP_200_OK

        result = json_resp.json()["result"]
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
            # Verify timestamp format (ISO string)
            assert isinstance(used_code["usedAt"], str)

        for unused_code in unused_codes:
            assert unused_code["usedAt"] is None

        # Test download endpoint
        download_resp = await client.get(self.recovery_codes_download_url)
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

        # Test JSON endpoint
        json_resp = await client.get(self.recovery_codes_url)
        assert json_resp.status_code == status.HTTP_401_UNAUTHORIZED

        # Test download endpoint
        download_resp = await client.get(self.recovery_codes_download_url)
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

        # Download
        resp = await client.get(self.recovery_codes_download_url)

        disposition = resp.headers.get("content-disposition", "")

        # Extract filename from header
        # Format: attachment; filename="recovery_codes_YYYYMMDD_HHMMSS.txt"
        match = re.search(r'filename="([^"]+)"', disposition)
        assert match is not None

        filename = match.group(1)

        # Validate format
        assert filename.startswith("recovery_codes_")
        assert filename.endswith(".txt")

        # Extract timestamp part
        # recovery_codes_20251125_170017.txt
        timestamp_part = filename.replace("recovery_codes_", "").replace(".txt", "")

        # Validate timestamp format YYYYMMDD_HHMMSS
        assert re.match(r"^\d{8}_\d{6}$", timestamp_part)
