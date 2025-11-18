""" Service for managing MFA authentication sessions using Redis. """
import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from config import settings
from infrastructure.utility.redis_client import RedisCache


class MFASessionData:
    """Data stored in MFA session."""

    def __init__(self, user_id: uuid.UUID, created_at: datetime):
        self.user_id = user_id
        self.created_at = created_at
    
    def to_dict(self) -> dict:
        """Convert to dictionary for REDIS storage."""
        return {
            "user_id": str(self.user_id),
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MFASessionData":
        """Create MFASessionData from dictionary."""
        return cls(
            user_id=uuid.UUID(data["user_id"]),
            created_at=datetime.fromisoformat(data["created_at"]),
        )

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
        Retrieve MFA session data from Redis.
        Args:
            mfa_session_id: The session identifier 
        Returns:
            MFASessionData if session exists and hasn't expired, None otherwise
        """
        redis_key = self._build_redis_key(mfa_session_id)
        session_json = await self.redis_client.get(redis_key)
        
        if not session_json:
            return None
        
        session_dict = json.loads(session_json)
        return MFASessionData.from_dict(session_dict)
    
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