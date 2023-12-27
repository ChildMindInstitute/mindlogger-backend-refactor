"""Update created_at from updated_at

Revision ID: 87d3c8a8de55
Revises: 60528d410fd1
Create Date: 2023-12-13 07:14:28.322481

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "87d3c8a8de55"
down_revision = "60528d410fd1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            update activity_histories
            set created_at = updated_at
            where migrated_date is not null
        """
        )
    )
    conn.execute(
        sa.text(
            """
            update activity_item_histories
            set created_at = updated_at
            where migrated_date is not null
        """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            with
            applets_created_at as (
                select
                    id,
                    created_at
                from applets
                where migrated_date is not null
            )
            update activity_histories
            set created_at = applets_created_at.created_at
            from applets_created_at
            where applets_created_at.id::text = split_part(applet_id, '_', 1)
                and migrated_date is not null
        """
        )
    )
    conn.execute(
        sa.text(
            """
            with
            activities_created_at as (
                select distinct
                    id_version,
                    created_at
                from activity_histories
                where migrated_date is not null
            )
            update activity_item_histories
            set created_at = activities_created_at.created_at
            from activities_created_at
            where activities_created_at.id_version = activity_id
                and migrated_date is not null
        """
        )
    )
