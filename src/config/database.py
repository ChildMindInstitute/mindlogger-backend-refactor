from os import getenv

from pydantic import BaseModel


class DatabaseSettings(BaseModel):

    url: str = "postgresql+asyncpg://" \
               "postgres:postgres@postgres:5432/mindlogger_backend"
    postgres_host: str = "postgres"
    postgres_password: str = "postgres"
    postgres_user: str = "postgres"
    postgres_db: str = "mindlogger_backend"
