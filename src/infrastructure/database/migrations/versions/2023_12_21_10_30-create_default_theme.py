"""Create default theme

Revision ID: b993457637ad
Revises: 87d3c8a8de55
Create Date: 2023-12-21 10:30:18.107063

"""
import datetime
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Boolean, DateTime, String, delete, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision = "b993457637ad"
down_revision = "87d3c8a8de55"
branch_labels = None
depends_on = None

THEMES_TABLE = table(
    "themes",
    column("id", UUID),
    column("name", String),
    column("primary_color", String),
    column("secondary_color", String),
    column("tertiary_color", String),
    column("creator_id", UUID),
    column("is_default", Boolean),
)
USERS_TABLE = table(
    "users",
    column("id", UUID),
    column("email", String),
    column("created_at", DateTime),
    column("updated_at", DateTime),
    column("is_deleted", Boolean),
    column("hashed_password", String),
    column("first_name", String),
    column("last_name", String),
    column("last_seen_at", DateTime),
)
FIRST_DEFAULT_THEME = {
    THEMES_TABLE.c.name: "First default theme",
    THEMES_TABLE.c.primary_color: "#FFFFFF",
    THEMES_TABLE.c.secondary_color: "#000000",
    THEMES_TABLE.c.tertiary_color: "#AAAAAA",
    THEMES_TABLE.c.is_default: True,
}
FIRST_DEFAULT_USER = "system_user_for_first_theme"


def upgrade() -> None:
    conn = op.get_bind()
    count_themes_query = select(
        select(THEMES_TABLE).where(THEMES_TABLE.c.is_default == True).exists()
    )
    is_default_themes_exists = conn.execute(count_themes_query).first()[0]
    if not is_default_themes_exists:
        current_datetime = datetime.datetime.utcnow()
        user = conn.execute(
            select(column("id", UUID))
            .select_from(USERS_TABLE)
            .where(USERS_TABLE.c.email == FIRST_DEFAULT_USER)
        ).first()
        if user:
            user_id = user[0]
        else:
            user_id = f"{uuid.uuid4()}"
            op.bulk_insert(
                USERS_TABLE,
                rows=[
                    {
                        "id": user_id,
                        "email": FIRST_DEFAULT_USER,
                        "created_at": current_datetime,
                        "updated_at": current_datetime,
                        "is_deleted": False,
                        "hashed_password": FIRST_DEFAULT_USER,
                        "first_name": FIRST_DEFAULT_USER,
                        "last_name": FIRST_DEFAULT_USER,
                        "last_seen_at": current_datetime,
                    },
                ],
            )

        first_theme = {
            f"{k.name}": v for (k, v) in FIRST_DEFAULT_THEME.items()
        }
        first_theme[f"{THEMES_TABLE.c.creator_id.name}"] = user_id
        first_theme[f"{THEMES_TABLE.c.id.name}"] = f"{uuid.uuid4()}"
        op.bulk_insert(THEMES_TABLE, rows=[first_theme])


def downgrade() -> None:
    conn = op.get_bind()
    first_theme_where = [k == v for (k, v) in FIRST_DEFAULT_THEME.items()]
    first_default_theme_in_db: tuple | None = conn.execute(
        select(column("id", UUID), column("creator_id", UUID))
        .select_from(THEMES_TABLE)
        .where(*first_theme_where)
    ).first()

    if first_default_theme_in_db:
        theme_id, theme_creator_id = first_default_theme_in_db
        conn.execute(delete(THEMES_TABLE).where(THEMES_TABLE.c.id == theme_id))
        first_default_user_in_db: tuple | None = conn.execute(
            select(column("id", UUID))
            .select_from(USERS_TABLE)
            .where(
                USERS_TABLE.c.id == theme_creator_id,
                USERS_TABLE.c.email == FIRST_DEFAULT_USER,
            )
        ).first()

        if first_default_user_in_db:
            creator_id = first_default_user_in_db[0]
            conn.execute(
                delete(USERS_TABLE).where(USERS_TABLE.c.id == creator_id)
            )
