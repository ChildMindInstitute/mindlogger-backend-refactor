"""Create jobs table

Revision ID: 8469536f11b3
Revises: 5c717b96fb99
Create Date: 2023-09-20 11:54:58.119206

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8469536f11b3"
down_revision = "5c717b96fb99"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "jobs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("timezone('utc', now())"),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("timezone('utc', now())"),
            nullable=True,
        ),
        sa.Column("migrated_date", sa.DateTime(), nullable=True),
        sa.Column("migrated_updated", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "in_progress", "success", "error", "retry", name="job_status"
            ),
            nullable=False,
        ),
        sa.Column(
            "details", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.id"],
            name=op.f("fk_jobs_creator_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_jobs")),
    )
    op.create_index(
        "unique_user_job_name", "jobs", ["creator_id", "name"], unique=True
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("unique_user_job_name", table_name="jobs")
    op.drop_table("jobs")
    sa.Enum(name="job_status").drop(op.get_bind(), checkfirst=False)
    # ### end Alembic commands ###
