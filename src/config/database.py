from os import getenv

from pydantic import BaseModel


class DatabaseSettings(BaseModel):

    database_url: str = getenv(
        "DATABASE_URL",
        default=(
            "postgresql+asyncpg://"
            "postgres:postgres@postgres:5432/mindlogger_backend"
        ),
    )
    postgres_host: str = getenv(
        "POSTGRES_HOST",
        default=(
            "postgres"
        ),
    )
    postgres_password: str = getenv(
        "POSTGRES_PASSWORD",
        default=(
            "postgres"
        ),
    )
    postgres_user: str = getenv(
        "POSTGRES_USER",
        default=(
            "postgres"
        ),
    )
    postgres_db: str = getenv(
        "POSTGRES_DB",
        default=(
            "mindlogger_backend"
        ),
    )
