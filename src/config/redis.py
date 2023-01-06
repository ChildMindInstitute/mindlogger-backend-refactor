from pydantic import BaseModel


class RedisSettings(BaseModel):
    """Configure redis settings"""

    host: str = "redis"
    port: str = "6379"
    db: str = "0"
    default_ttl: int = 3600

    @property
    def url(self) -> str:
        return f"redis://{self.host}:{self.port}/db{self.db}"
