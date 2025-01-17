from pydantic import BaseModel


class DatabaseSettings(BaseModel):
    host: str = "postgres"
    port: int = 5432
    password: str = "postgres"
    user: str = "postgres"
    db: str = "mindlogger_backend"
    pool_size: int = 2

    @property
    def url(self) -> str:
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
