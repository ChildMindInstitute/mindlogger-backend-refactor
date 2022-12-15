from pydantic import BaseModel


class DatabaseSettings(BaseModel):
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_password: str = "postgres"
    postgres_user: str = "postgres"
    postgres_db: str = "mindlogger_backend"
    pool_size: int = 2

    @property
    def url(self) -> str:
        return (
            "postgresql+asyncpg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
