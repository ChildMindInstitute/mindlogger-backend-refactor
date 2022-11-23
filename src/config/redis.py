from pydantic import BaseModel


class RedisSettings(BaseModel):
    """Configure redis settings"""

    dsn: str = ""
    host: str = ""
    port: str = ""
    db: str = ""
    expire_duration: int = None
    env: str = ""
