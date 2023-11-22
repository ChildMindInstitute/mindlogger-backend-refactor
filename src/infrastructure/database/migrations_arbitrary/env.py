import asyncio
import os
from logging.config import fileConfig

from alembic import context
from alembic.config import Config
from sqlalchemy import MetaData, Unicode, engine_from_config, pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from config import settings
from infrastructure.database.migrations.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override alembic.ini option
config.set_main_option("sqlalchemy.url", settings.database.url)
arbitrary_urls = []


async def get_all_servers(connection):
    try:
        query = text(
            """
            SELECT uw.database_uri
            FROM users_workspaces as uw
            WHERE uw.database_uri is not null
        """
        )
        rows = await connection.execute(query)
        urls_encrypted = map(lambda r: r[0], rows.fetchall())
        urls = list(
            map(
                lambda enc_value: StringEncryptedType(
                    Unicode, get_key
                ).process_result_value(enc_value, dialect=connection.dialect),
                urls_encrypted,
            )
        )
    except Exception as ex:
        print(ex)
        urls = []
    if os.environ.get("PYTEST_APP_TESTING"):
        arbitrary_db_name = os.environ["ARBITRARY_DB"]
        url = settings.database.url.replace("/test", f"/{arbitrary_db_name}")
        urls.append(url)
    return urls


async def get_urls():
    global arbitrary_urls
    connectable = create_async_engine(url=settings.database.url)
    async with connectable.connect() as connection:
        arbitrary_urls = await get_all_servers(connection)
    await connectable.dispose()


async def migrate_arbitrary():
    global arbitrary_urls
    arbitrary_meta = MetaData()
    arbitrary_tables = [
        Base.metadata.tables["answers"],
        Base.metadata.tables["answers_items"],
    ]
    arbitrary_meta.tables = arbitrary_tables
    for url in arbitrary_urls:
        config.set_main_option("sqlalchemy.url", url)
        connectable = AsyncEngine(
            engine_from_config(
                config.get_section(config.config_ini_section),
                prefix="sqlalchemy.",
                poolclass=pool.NullPool,
                future=True,
            )
        )
        async with connectable.connect() as connection:
            await connection.run_sync(
                do_run_migrations, arbitrary_meta, config
            )
        await connectable.dispose()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    context.configure(
        url=settings.database.url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(
    connection: Connection,
    metadata: MetaData = target_metadata,
    alembic_config: Config = config,
) -> None:
    context.configure(
        connection=connection, target_metadata=metadata, config=alembic_config
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    await get_urls()
    await migrate_arbitrary()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
