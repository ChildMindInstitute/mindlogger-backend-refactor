from pydantic import BaseModel


class RedisSettings(BaseModel):
    """Configure redis settings"""

    host: str = "redis"
    port: int = 6379
    db: int = 0
    default_ttl: int = 3600
    mfa_session_ttl: int = 300 # 5 minutes for MFA sessions

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/db{self.db}"
