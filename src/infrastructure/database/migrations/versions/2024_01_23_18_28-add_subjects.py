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
down_revision = "46f285831ae8"
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
    op.create_table(
        "subject_respondents",
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
            "respondent_access_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(
            ["respondent_access_id"],
            ["user_applet_accesses.id"],
            name=op.f(
                "fk_subject_respondents_respondent_access_id_user_applet_accesses"
            ),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["subject_id"],
            ["subjects.id"],
            name=op.f("fk_subject_respondents_subject_id_subjects"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_subject_respondents")),
        sa.UniqueConstraint(
            "relation", name=op.f("uq_subject_respondents_relation")
        ),
    )
    op.create_index(
        "unique_subject_user_applet",
        "subjects",
        ["user_id", "applet_id"],
        unique=True,
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("unique_subject_user_applet", table_name="subjects")
    op.drop_table("subject_respondents")
    op.drop_table("subjects")
    # ### end Alembic commands ###
