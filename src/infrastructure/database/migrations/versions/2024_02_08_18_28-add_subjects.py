"""Add subjects

Revision ID: edb2781f141b
Revises: 3fb536a58c94
Create Date: 2024-01-05 18:28:37.879517

"""
import sqlalchemy as sa
import sqlalchemy_utils
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "edb2781f141b"
down_revision = "736adb0ea547"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "subjects",
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
        sa.Column("applet_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column(
            "email",
            sqlalchemy_utils.types.encrypted.encrypted_type.StringEncryptedType(),
            nullable=True,
        ),
        sa.Column(
            "nickname",
            sqlalchemy_utils.types.encrypted.encrypted_type.StringEncryptedType(),
            nullable=True
        ),
        sa.Column(
            "first_name",
            sqlalchemy_utils.types.encrypted.encrypted_type.StringEncryptedType(),
            nullable=False,
        ),
        sa.Column(
            "last_name",
            sqlalchemy_utils.types.encrypted.encrypted_type.StringEncryptedType(),
            nullable=False,
        ),
        sa.Column("secret_user_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ["applet_id"],
            ["applets.id"],
            name=op.f("fk_subjects_applet_id_applets"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.id"],
            name=op.f("fk_subjects_creator_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_subjects_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subjects")),
    )
    op.create_index(
        "ix_subjects_user_id",
        "subjects",
        ["user_id", "applet_id"],
        unique=True,
    )
    op.create_index(
        "ix_subjects_applet_id",
        "subjects",
        ["applet_id", "secret_user_id"],
        unique=True,
    )
    op.create_table(
        "subject_relations",
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
        sa.Column(
            "source_subject_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column(
            "target_subject_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
        sa.Column("relation", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_subject_id"],
            ["subjects.id"],
            name=op.f("fk_subject_relations_source_subject_id_subjects"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["target_subject_id"],
            ["subjects.id"],
            name=op.f("fk_subject_relations_target_subject_id_subjects"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subject_relations")),
    )
    op.create_index(
        op.f("ix_subject_relations_source_subject_id"),
        "subject_relations",
        ["source_subject_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_subject_relations_target_subject_id"),
        "subject_relations",
        ["target_subject_id"],
        unique=False,
    )
    op.create_index(
        "uq_subject_relations_source_target",
        "subject_relations",
        ["source_subject_id", "target_subject_id"],
        unique=True,
    )

    op.add_column(
        "alerts",
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        op.f("fk_alerts_subject_id_subjects"),
        "alerts",
        "subjects",
        ["subject_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.add_column(
        "user_pins",
        sa.Column(
            "pinned_subject_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.alter_column(
        "user_pins",
        "pinned_user_id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )
    op.create_foreign_key(
        op.f("fk_user_pins_pinned_subject_id_subjects"),
        "user_pins",
        "subjects",
        ["pinned_subject_id"],
        ["id"],
        ondelete="CASCADE",
    )


    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        op.f("fk_alerts_subject_id_subjects"), "alerts", type_="foreignkey"
    )
    op.drop_column("alerts", "subject_id")

    op.drop_index(
        "uq_subject_relations_source_target", table_name="subject_relations"
    )
    op.drop_index(
        op.f("ix_subject_relations_target_subject_id"),
        table_name="subject_relations",
    )
    op.drop_index(
        op.f("ix_subject_relations_source_subject_id"),
        table_name="subject_relations",
    )
    op.drop_table("subject_relations")

    op.drop_index("ix_subjects_user_id", table_name="subjects")
    op.drop_index("ix_subjects_applet_id", table_name="subjects")
    op.drop_constraint(op.f("fk_user_pins_pinned_subject_id_subjects"), "user_pins", type_="foreignkey")
    op.alter_column(
        "user_pins",
        "pinned_user_id",
        existing_type=postgresql.UUID(),
        nullable=False
    )
    op.drop_column("user_pins", "pinned_subject_id")
    op.drop_table("subjects")
    # ### end Alembic commands ###
