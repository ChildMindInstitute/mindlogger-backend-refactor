import pytest
import pyotp
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from apps.users import UsersCRUD
from apps.users.domain import User
from apps.users.router import router as user_router
from apps.users.services.totp import totp_service
from apps.shared.test.client import TestClient


@pytest.mark.usefixtures("user")
class TestMFAEndpoints:
    """Integration tests for MFA TOTP endpoints."""
    
    totp_initiate_url = "/users/me/mfa/totp/initiate"
    totp_verify_url = "/users/me/mfa/totp/verify"
    user_retrieve_url = user_router.url_path_for("user_retrieve")

    async def test_mfa_totp_initiate_success(self, client: TestClient, user: User):
        """Test successful TOTP initiation."""
        client.login(user)
        
        response = await client.post(self.totp_initiate_url)
        
        assert response.status_code == status.HTTP_200_OK
        result = response.json()["result"]
        
        # Check response structure
        assert "provisioningUri" in result
        assert "message" in result
        
        # Validate provisioning URI format
        uri = result["provisioningUri"]
        assert uri.startswith("otpauth://totp/")
        # Email is URL-encoded in the URI (@ becomes %40)
        assert "user%40example.com" in uri or user.email_encrypted in uri
        assert "secret=" in uri
        assert "issuer=" in uri

    async def test_mfa_totp_initiate_stores_pending_secret(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Test that initiation stores encrypted secret in database."""
        client.login(user)
        
        response = await client.post(self.totp_initiate_url)
        assert response.status_code == status.HTTP_200_OK
        
        # Fetch user from DB to verify pending secret
        crud = UsersCRUD(session)
        updated_user = await crud.get_by_id(user.id)
        
        assert updated_user.pending_mfa_secret is not None
        assert updated_user.pending_mfa_created_at is not None
        assert updated_user.mfa_enabled is False
        assert updated_user.mfa_secret is None

    async def test_mfa_totp_initiate_replaces_previous_pending(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Test that initiating again replaces previous pending setup."""
        client.login(user)
        
        # First initiation
        response1 = await client.post(self.totp_initiate_url)
        assert response1.status_code == status.HTTP_200_OK
        uri1 = response1.json()["result"]["provisioningUri"]
        
        # Second initiation
        response2 = await client.post(self.totp_initiate_url)
        assert response2.status_code == status.HTTP_200_OK
        uri2 = response2.json()["result"]["provisioningUri"]
        
        # URIs should be different (new secret generated)
        assert uri1 != uri2

    async def test_mfa_totp_verify_success(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Test successful TOTP verification and MFA activation."""
        client.login(user)
        
        # Step 1: Initiate TOTP setup
        response = await client.post(self.totp_initiate_url)
        assert response.status_code == status.HTTP_200_OK
        
        # Extract secret from provisioning URI
        uri = response.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]
        
        # Generate valid TOTP code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Step 2: Verify TOTP code
        verify_response = await client.post(
            self.totp_verify_url,
            data={"code": valid_code}
        )
        
        assert verify_response.status_code == status.HTTP_200_OK
        result = verify_response.json()["result"]
        
        assert result["mfaEnabled"] is True
        assert "successfully enabled" in result["message"]
        
        # Step 3: Verify user in DB has MFA enabled
        crud = UsersCRUD(session)
        updated_user = await crud.get_by_id(user.id)
        
        assert updated_user.mfa_enabled is True
        assert updated_user.mfa_secret is not None
        assert updated_user.pending_mfa_secret is None
        assert updated_user.pending_mfa_created_at is None

    async def test_mfa_totp_verify_invalid_code(self, client: TestClient, user: User):
        """Test verification fails with invalid TOTP code."""
        client.login(user)
        
        # Initiate setup
        await client.post(self.totp_initiate_url)
        
        # Try to verify with invalid code
        response = await client.post(
            self.totp_verify_url,
            data={"code": "000000"}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error = response.json()["result"][0]
        assert error["message"] == "Invalid TOTP code. Please check your authenticator app and try again."

    async def test_mfa_totp_verify_without_initiation(self, client: TestClient, user: User):
        """Test verification fails without prior initiation."""
        client.login(user)
        
        # Try to verify without initiating
        response = await client.post(
            self.totp_verify_url,
            data={"code": "123456"}
        )
        
        # MFASetupNotFoundError returns 404 (NotFoundError)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        error = response.json()["result"][0]
        assert error["message"] == "No pending MFA setup found. Please initiate MFA setup first."

    async def test_mfa_totp_verify_expired_setup(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Test verification fails with expired pending setup."""
        client.login(user)
        
        # Initiate setup
        response = await client.post(self.totp_initiate_url)
        uri = response.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]
        
        # Manually expire the pending setup by backdating created_at
        from datetime import datetime, timedelta, timezone
        crud = UsersCRUD(session)
        user_db = await crud.get_by_id(user.id)
        
        # Set created_at to 15 minutes ago (default expiration is 10 minutes)
        expired_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=15)
        await crud.update_pending_mfa(
            user_id=user.id,
            encrypted_secret=user_db.pending_mfa_secret,
            created_at=expired_time
        )
        await session.commit()
        
        # Generate valid code
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        # Try to verify - should fail due to expiration
        response = await client.post(
            self.totp_verify_url,
            data={"code": valid_code}
        )
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error = response.json()["result"][0]
        assert "expired" in error["message"].lower()

    async def test_mfa_totp_verify_invalid_code_format(self, client: TestClient, user: User):
        """Test verification rejects invalid code formats."""
        client.login(user)
        
        # Initiate setup
        await client.post(self.totp_initiate_url)
        
        # Try with non-6-digit code
        response = await client.post(
            self.totp_verify_url,
            data={"code": "12345"}  # Only 5 digits
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_mfa_status_in_user_retrieve(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Test that /users/me returns mfaEnabled status."""
        client.login(user)
        
        # Check initial MFA status (should be false)
        response = await client.get(self.user_retrieve_url)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()["result"]
        assert result["mfaEnabled"] is False
        
        # Enable MFA
        init_response = await client.post(self.totp_initiate_url)
        uri = init_response.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]
        
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        await client.post(self.totp_verify_url, data={"code": valid_code})
        
        # Check MFA status again (should be true)
        response = await client.get(self.user_retrieve_url)
        assert response.status_code == status.HTTP_200_OK
        result = response.json()["result"]
        assert result["mfaEnabled"] is True

    async def test_mfa_totp_verify_requires_authentication(self, client: TestClient):
        """Test that MFA endpoints require authentication."""
        # Try without login
        response = await client.post(self.totp_initiate_url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        response = await client.post(self.totp_verify_url, data={"code": "123456"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_mfa_encrypted_secret_storage(
        self, client: TestClient, user: User, session: AsyncSession
    ):
        """Test that secrets are stored encrypted in database."""
        client.login(user)
        
        # Initiate and complete setup
        init_response = await client.post(self.totp_initiate_url)
        uri = init_response.json()["result"]["provisioningUri"]
        secret = uri.split("secret=")[1].split("&")[0]
        
        totp = pyotp.TOTP(secret)
        valid_code = totp.now()
        
        await client.post(self.totp_verify_url, data={"code": valid_code})
        
        # Fetch user from DB
        crud = UsersCRUD(session)
        updated_user = await crud.get_by_id(user.id)
        
        # Stored secret should NOT be the plain text secret
        assert updated_user.mfa_secret != secret
        
        # Should be able to decrypt it back to original
        decrypted = totp_service.decrypt_secret(updated_user.mfa_secret)
        assert decrypted == secret
