from pydantic import BaseModel
from urllib.parse import urlparse, unquote


class DatabaseSettings(BaseModel):
    host: str = "postgres"
    port: int = 5432
    password: str = "postgres"
    user: str = "postgres"
    db: str = "mindlogger_backend"
    pool_size: int = 5
    pool_overflow_size: int = 10
    pool_timeout: int = 30

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"

    @classmethod
    def from_connection_string(cls, connection_string: str):
        """Generate database settings from a connection string.  Useful for tests."""
        parsed = urlparse(connection_string)

        if not parsed.scheme:
            raise ValueError("Connection string is missing a scheme")

        if not parsed.hostname:
            raise ValueError("Connection string is missing a host")

        return cls(user=parsed.username, password=unquote(parsed.password), host=parsed.hostname, port=parsed.port, db=parsed.path.lstrip("/")
        )
