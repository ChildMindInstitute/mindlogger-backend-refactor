"""Cron removing expired blacklisted tokens

Revision ID: 69b1dfaf3c0d
Revises: 75c9ca1f506b
Create Date: 2023-11-29 17:08:41.800439

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

from config import settings

# revision identifiers, used by Alembic.
revision = "69b1dfaf3c0d"
down_revision = "75c9ca1f506b"
branch_labels = None
depends_on = None

task_name = "clear_token_blacklist"
schedule = "0 9 * * *"
query = text(
    "delete from token_blacklist " "where \"exp\" < now() at time zone 'utc'"
)


def upgrade() -> None:
    if settings.env != "testing":
        op.execute(
            text(
                f"SELECT cron.schedule(:task_name, :schedule, $${query}$$);"
            ).bindparams(task_name=task_name, schedule=schedule)
        )


def downgrade() -> None:
    if settings.env != "testing":
        op.execute(
            text(f"SELECT cron.unschedule(:task_name);").bindparams(
                task_name=task_name
            )
        )
