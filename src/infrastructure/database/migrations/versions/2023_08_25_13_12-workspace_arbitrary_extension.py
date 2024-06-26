"""workspase arbitrary extension

Revision ID: f90a62f155cc
Revises: 8cd84b8900cc
Create Date: 2023-08-15 13:12:49.093560

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f90a62f155cc"
down_revision = "8cd84b8900cc"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(
        op.f("ix_answer_notes_answer_id"),
        "answer_notes",
        ["answer_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_answer_notes_user_id"),
        "answer_notes",
        ["user_id"],
        unique=False,
    )
    op.drop_constraint(
        "fk_answer_notes_answer_id_answers", "answer_notes", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_answer_notes_user_id_users", "answer_notes", type_="foreignkey"
    )
    op.create_index(
        op.f("ix_answers_activity_history_id"),
        "answers",
        ["activity_history_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_answers_applet_history_id"),
        "answers",
        ["applet_history_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_answers_applet_id"), "answers", ["applet_id"], unique=False
    )
    op.create_index(
        op.f("ix_answers_flow_history_id"),
        "answers",
        ["flow_history_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_answers_respondent_id"),
        "answers",
        ["respondent_id"],
        unique=False,
    )
    op.drop_constraint(
        "fk_answers_respondent_id_users", "answers", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_answers_applet_history_id_applet_histories",
        "answers",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_answers_flow_history_id_flow_histories",
        "answers",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_answers_activity_history_id_activity_histories",
        "answers",
        type_="foreignkey",
    )
    op.create_index(
        op.f("ix_answers_items_respondent_id"),
        "answers_items",
        ["respondent_id"],
        unique=False,
    )
    op.drop_constraint(
        "fk_answers_items_respondent_id_users",
        "answers_items",
        type_="foreignkey",
    )
    op.add_column(
        "users_workspaces",
        sa.Column("database_uri", sa.String(), nullable=True),
    )
    op.add_column(
        "users_workspaces",
        sa.Column("storage_type", sa.String(), nullable=True),
    )
    op.add_column(
        "users_workspaces",
        sa.Column("storage_access_key", sa.String(), nullable=True),
    )
    op.add_column(
        "users_workspaces",
        sa.Column("storage_secret_key", sa.String(), nullable=True),
    )
    op.add_column(
        "users_workspaces",
        sa.Column("storage_region", sa.String(), nullable=True),
    )
    op.add_column(
        "users_workspaces",
        sa.Column("storage_url", sa.String(), nullable=True),
    )
    op.add_column(
        "users_workspaces",
        sa.Column("storage_bucket", sa.String(), nullable=True),
    )
    op.add_column(
        "users_workspaces",
        sa.Column("use_arbitrary", sa.Boolean(), nullable=True),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users_workspaces", "use_arbitrary")
    op.drop_column("users_workspaces", "storage_bucket")
    op.drop_column("users_workspaces", "storage_url")
    op.drop_column("users_workspaces", "storage_region")
    op.drop_column("users_workspaces", "storage_secret_key")
    op.drop_column("users_workspaces", "storage_access_key")
    op.drop_column("users_workspaces", "storage_type")
    op.drop_column("users_workspaces", "database_uri")
    op.create_foreign_key(
        "fk_answers_items_respondent_id_users",
        "answers_items",
        "users",
        ["respondent_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_index(
        op.f("ix_answers_items_respondent_id"), table_name="answers_items"
    )
    op.create_foreign_key(
        "fk_answers_activity_history_id_activity_histories",
        "answers",
        "activity_histories",
        ["activity_history_id"],
        ["id_version"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_answers_flow_history_id_flow_histories",
        "answers",
        "flow_histories",
        ["flow_history_id"],
        ["id_version"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_answers_applet_history_id_applet_histories",
        "answers",
        "applet_histories",
        ["applet_history_id"],
        ["id_version"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_answers_respondent_id_users",
        "answers",
        "users",
        ["respondent_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_index(op.f("ix_answers_respondent_id"), table_name="answers")
    op.drop_index(op.f("ix_answers_flow_history_id"), table_name="answers")
    op.drop_index(op.f("ix_answers_applet_id"), table_name="answers")
    op.drop_index(op.f("ix_answers_applet_history_id"), table_name="answers")
    op.drop_index(op.f("ix_answers_activity_history_id"), table_name="answers")
    op.create_foreign_key(
        "fk_answer_notes_user_id_users",
        "answer_notes",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_answer_notes_answer_id_answers",
        "answer_notes",
        "answers",
        ["answer_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_index(op.f("ix_answer_notes_user_id"), table_name="answer_notes")
    op.drop_index(op.f("ix_answer_notes_answer_id"), table_name="answer_notes")
    # ### end Alembic commands ###
