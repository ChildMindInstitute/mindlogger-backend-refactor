"""Create default theme

Revision ID: b993457637ad
Revises: 87d3c8a8de55
Create Date: 2023-12-21 10:30:18.107063

"""
import datetime
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy import Boolean, String, delete, select
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
FIRST_DEFAULT_THEME = {
    THEMES_TABLE.c.name: "First default theme",
    THEMES_TABLE.c.primary_color: "#FFFFFF",
    THEMES_TABLE.c.secondary_color: "#000000",
    THEMES_TABLE.c.tertiary_color: "#AAAAAA",
    THEMES_TABLE.c.is_default: True,
}


def upgrade() -> None:
    op.alter_column(
        "themes", "creator_id", existing_type=UUID(), nullable=True
    )

    conn = op.get_bind()
    count_themes_query = select(
        select(THEMES_TABLE).where(THEMES_TABLE.c.is_default == True).exists()
    )
    is_default_themes_exists = conn.execute(count_themes_query).first()[0]
    if not is_default_themes_exists:
        first_theme = {
            f"{k.name}": v for (k, v) in FIRST_DEFAULT_THEME.items()
        }
        first_theme[f"{THEMES_TABLE.c.id.name}"] = f"{uuid.uuid4()}"
        op.bulk_insert(THEMES_TABLE, rows=[first_theme])


def downgrade() -> None:
    conn = op.get_bind()
    first_theme_where = [k == v for (k, v) in FIRST_DEFAULT_THEME.items()]
    first_default_theme_in_db: tuple | None = conn.execute(
        select(column("id", UUID))
        .select_from(THEMES_TABLE)
        .where(*first_theme_where)
    ).first()

    if first_default_theme_in_db:
        theme_id = first_default_theme_in_db[0]
        conn.execute(delete(THEMES_TABLE).where(THEMES_TABLE.c.id == theme_id))

    op.alter_column(
        "themes", "creator_id", existing_type=UUID(), nullable=False
    )
