"""update folder

Revision ID: b8a742bc9b35
Revises: 54b497530baf
Create Date: 2023-05-17 15:49:09.743333

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "b8a742bc9b35"
down_revision = "54b497530baf"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "folder_applets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=True),
        sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("applet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pinned_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["applet_id"],
            ["applets.id"],
            name=op.f("fk_folder_applets_applet_id_applets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["folder_id"],
            ["folders.id"],
            name=op.f("fk_folder_applets_folder_id_folders"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_folder_applets")),
    )
    op.drop_constraint(
        "fk_applets_folder_id_folders", "applets", type_="foreignkey"
    )
    op.drop_column("applets", "folder_id")

    op.execute("""
        delete from folders;
    """)

    op.add_column(
        "folders",
        sa.Column(
            "workspace_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
    )
    op.create_foreign_key(
        op.f("fk_folders_workspace_id_users"),
        "folders",
        "users",
        ["workspace_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        op.f("fk_folders_workspace_id_users"), "folders", type_="foreignkey"
    )
    op.drop_column("folders", "workspace_id")
    op.add_column(
        "applets",
        sa.Column(
            "folder_id", postgresql.UUID(), autoincrement=False, nullable=True
        ),
    )
    op.create_foreign_key(
        "fk_applets_folder_id_folders",
        "applets",
        "folders",
        ["folder_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_table("folder_applets")
    # ### end Alembic commands ###
