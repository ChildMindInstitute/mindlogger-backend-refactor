"""Service for managing MFA authentication sessions using Redis."""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from config import settings
from infrastructure.utility.redis_client import RedisCache


class MFASessionData:
    """Data stored in MFA session."""

    def __init__(self, user_id: uuid.UUID, created_at: datetime, failed_totp_attempts: int = 0):
        self.user_id = user_id
        self.created_at = created_at
        self.failed_totp_attempts = failed_totp_attempts

    def to_dict(self) -> dict:
        """Convert to dictionary for REDIS storage."""
        return {
            "user_id": str(self.user_id),
            "created_at": self.created_at.isoformat(),
            "failed_totp_attempts": self.failed_totp_attempts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MFASessionData":
        """Create MFASessionData from dictionary."""
        return cls(
            user_id=uuid.UUID(data["user_id"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            failed_totp_attempts=data.get("failed_totp_attempts", 0),  # Default to 0 
        )
    
    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if the session is expired based on TTL."""
        now = datetime.now(timezone.utc)
        session_age_in_seconds = (now - self.created_at).total_seconds()
        return session_age_in_seconds > ttl_seconds
    
    def get_age_seconds(self) -> float:
        """Get the age of the session in seconds."""
        now = datetime.now(timezone.utc)
        return (now - self.created_at).total_seconds()
    
    def increment_failed_attempts(self):
        """Increment the count of failed TOTP attempts."""
        self.failed_totp_attempts += 1
        return self.failed_totp_attempts
    
    def has_exceeded_max_attempts(self, max_attempts: int) -> bool:
        """Check if failed attempts have exceeded max allowed."""
        return self.failed_totp_attempts >= max_attempts


class MFASessionService:
    """Service for managing MFA Authentication in Redis."""

    def __init__(self):
        self.redis_client = RedisCache()
        self.session_ttl = settings.redis.mfa_session_ttl

    def _build_redis_key(self, mfa_session_id: str) -> str:
        """
        Build Redis key for MFA session.
        Format: mfa_session:<session_id>
        Example: mfa_session:a7b3f2e1-4d5c-6789-0abc-def123456789
        """
        return f"mfa_session:{mfa_session_id}"
    
    def _validate_session_id_format(self, mfa_session_id: str) -> bool:
        """Validate that the session ID is a valid UUID string."""
        if not mfa_session_id or not isinstance(mfa_session_id, str):
            return False
        
        try:
            uuid.UUID(mfa_session_id)
            return True
        except (ValueError, AttributeError, TypeError):
            return False

    async def create_session(self, user_id: uuid.UUID) -> str:
        """
        Create a new MFA session in Redis.
        Args:
            user_id (uuid.UUID): ID of the user starting MFA.
        Returns:
            mfa_session_id: A unique session identifier to be sent to the client.
        """
        # Generate unique session ID
        mfa_session_id = str(uuid.uuid4())

        # Create session data
        session_data = MFASessionData(
            user_id=user_id,
            created_at=datetime.now(timezone.utc),
        )

        # Store in Redis with TTL
        redis_key = self._build_redis_key(mfa_session_id)
        await self.redis_client.set(
            key=redis_key,
            value=json.dumps(session_data.to_dict()),
            ex=self.session_ttl,
        )

        return mfa_session_id

    async def get_session(self, mfa_session_id: str) -> Optional[MFASessionData]:
        """
        Retrieve MFA session data from Redis with validation.
        
        Validates:
        - Session ID format (must be valid UUID)
        - JSON parsing (handles corrupted data)
        - Session age (defense against clock skew)
        
        Args:
            mfa_session_id: The session identifier
            
        Returns:
            MFASessionData if session exists and is valid, None otherwise
        """
        # Validate session ID format first
        if not self._validate_session_id_format(mfa_session_id):
            return None
        
        redis_key = self._build_redis_key(mfa_session_id)
        session_json = await self.redis_client.get(redis_key)

        if not session_json:
            return None

        # Handle corrupted or invalid JSON data
        try:
            session_dict = json.loads(session_json)
            session_data = MFASessionData.from_dict(session_dict)
            
            # Double-check expiration
            if session_data.is_expired(self.session_ttl):
                # Session exceeded TTL, clean it up
                await self.delete_session(mfa_session_id)
                return None
            
            return session_data
            
        except (json.JSONDecodeError, KeyError, ValueError, TypeError):
            # Session data is corrupted, delete it to clean up
            await self.delete_session(mfa_session_id)
            return None

    async def delete_session(self, mfa_session_id: str) -> bool:
        """
        Delete MFA session from Redis.
        Args:
            mfa_session_id: The session identifier
        Returns:
            True if session was deleted, False otherwise
        """
        redis_key = self._build_redis_key(mfa_session_id)
        return await self.redis_client.delete(redis_key)
    
    async def increment_failed_totp_attempts(self, mfa_session_id: str) -> Optional[int]:
        """
        Increment the count of failed TOTP attempts for the session.
        
        Args:
            mfa_session_id: The session identifier
        Returns:
            The updated count of failed attempts, or None if session not found
        """
        # Get existing session
        session_data = await self.get_session(mfa_session_id)

        if not session_data:
            return None
        
        # Increment failed attempts
        new_count = session_data.increment_failed_attempts()

        # Update session in Redis with original TTL
        # Note: We use the full session_ttl since the session is still valid
        redis_key = self._build_redis_key(mfa_session_id)
        await self.redis_client.set(
            key=redis_key,
            value=json.dumps(session_data.to_dict()),
            ex=self.session_ttl,
        )
        return new_count