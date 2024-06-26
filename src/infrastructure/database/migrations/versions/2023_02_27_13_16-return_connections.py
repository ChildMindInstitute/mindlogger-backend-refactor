"""return connections

Revision ID: 3fb3cd7bd906
Revises: 8f62ff76eba0
Create Date: 2023-02-27 13:16:58.036665

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "3fb3cd7bd906"
down_revision = "8f62ff76eba0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "activities",
        sa.Column("applet_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "transfer_ownership",
        sa.Column("applet_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "activity_events",
        sa.Column(
            "activity_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
    )
    op.add_column(
        "activity_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "activity_items",
        sa.Column(
            "activity_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
    )
    op.add_column(
        "answers_activity_items",
        sa.Column(
            "respondent_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
    )
    op.add_column(
        "answers_activity_items",
        sa.Column("applet_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "answers_activity_items",
        sa.Column(
            "activity_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
    )
    op.add_column(
        "answers_flow_items",
        sa.Column(
            "respondent_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
    )
    op.add_column(
        "answers_flow_items",
        sa.Column("applet_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "applet_histories",
        sa.Column("theme_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "applet_histories",
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "applet_histories",
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "applets",
        sa.Column("theme_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "applets",
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "applets",
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "applets",
        sa.Column("folder_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "events",
        sa.Column(
            "periodicity_id", postgresql.UUID(as_uuid=True), nullable=False
        ),
    )
    op.add_column(
        "events",
        sa.Column("applet_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "flow_events",
        sa.Column("flow_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "flow_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "flow_items",
        sa.Column(
            "activity_flow_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
    )
    op.add_column(
        "flow_items",
        sa.Column("activity_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "flows",
        sa.Column("applet_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "folders",
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "invitations",
        sa.Column("applet_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "invitations",
        sa.Column("invitor_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "reusable_item_choices",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "themes",
        sa.Column("creator_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "user_applet_accesses",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "user_applet_accesses",
        sa.Column("applet_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "user_events",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.add_column(
        "user_events",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
    )

    op.create_foreign_key(
        op.f("fk_activities_applet_id_applets"),
        "activities",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_transfer_ownership_applet_id_applets"),
        "transfer_ownership",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "_unique_activity_events", "activity_events", type_="unique"
    )
    op.create_unique_constraint(
        "_unique_activity_events",
        "activity_events",
        ["activity_id", "event_id", "is_deleted"],
    )
    op.create_foreign_key(
        op.f("fk_activity_events_event_id_events"),
        "activity_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "activity_histories",
        "id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )
    op.alter_column(
        "activity_item_histories",
        "id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )
    op.create_foreign_key(
        op.f("fk_activity_items_activity_id_activities"),
        "activity_items",
        "activities",
        ["activity_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_answers_activity_items_activity_id_activities"),
        "answers_activity_items",
        "activities",
        ["activity_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_answers_activity_items_applet_id_applets"),
        "answers_activity_items",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_answers_activity_items_respondent_id_users"),
        "answers_activity_items",
        "users",
        ["respondent_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_answers_flow_items_respondent_id_users"),
        "answers_flow_items",
        "users",
        ["respondent_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_answers_flow_items_applet_id_applets"),
        "answers_flow_items",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.alter_column(
        "applet_histories",
        "id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )
    op.create_foreign_key(
        op.f("fk_applet_histories_creator_id_users"),
        "applet_histories",
        "users",
        ["creator_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_applets_folder_id_folders"),
        "applets",
        "folders",
        ["folder_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_applets_creator_id_users"),
        "applets",
        "users",
        ["creator_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_events_applet_id_applets"),
        "events",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_events_periodicity_id_periodicity"),
        "events",
        "periodicity",
        ["periodicity_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("_unique_flow_events", "flow_events", type_="unique")
    op.create_unique_constraint(
        "_unique_flow_events",
        "flow_events",
        ["flow_id", "event_id", "is_deleted"],
    )
    op.create_foreign_key(
        op.f("fk_flow_events_event_id_events"),
        "flow_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column(
        "flow_histories", "id", existing_type=postgresql.UUID(), nullable=True
    )
    op.drop_column("flow_histories", "guid")
    op.alter_column(
        "flow_item_histories",
        "id",
        existing_type=postgresql.UUID(),
        nullable=True,
    )
    op.create_foreign_key(
        op.f("fk_flow_items_activity_id_activities"),
        "flow_items",
        "activities",
        ["activity_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_flow_items_activity_flow_id_flows"),
        "flow_items",
        "flows",
        ["activity_flow_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_flows_applet_id_applets"),
        "flows",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_column("flows", "guid")
    op.create_foreign_key(
        op.f("fk_folders_creator_id_users"),
        "folders",
        "users",
        ["creator_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_invitations_applet_id_applets"),
        "invitations",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_invitations_invitor_id_users"),
        "invitations",
        "users",
        ["invitor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint(
        "_unique_item_choices", "reusable_item_choices", type_="unique"
    )
    op.create_unique_constraint(
        "_unique_item_choices",
        "reusable_item_choices",
        ["user_id", "token_name", "token_value", "input_type"],
    )
    op.create_foreign_key(
        op.f("fk_reusable_item_choices_user_id_users"),
        "reusable_item_choices",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_themes_creator_id_users"),
        "themes",
        "users",
        ["creator_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_user_applet_accesses_applet_id"),
        "user_applet_accesses",
        ["applet_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_applet_accesses_user_id"),
        "user_applet_accesses",
        ["user_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_user_applet_accesses_applet_id_applets"),
        "user_applet_accesses",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        op.f("fk_user_applet_accesses_user_id_users"),
        "user_applet_accesses",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_constraint("_unique_user_events", "user_events", type_="unique")
    op.create_unique_constraint(
        "_unique_user_events",
        "user_events",
        ["user_id", "event_id", "is_deleted"],
    )
    op.create_foreign_key(
        op.f("fk_user_events_event_id_events"),
        "user_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("fk_user_events_user_id_users"),
        "user_events",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(
        op.f("fk_user_events_user_id_users"), "user_events", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("fk_transfer_ownership_applet_id_applets"),
        "transfer_ownership",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_user_events_event_id_events"),
        "user_events",
        type_="foreignkey",
    )
    op.drop_constraint("_unique_user_events", "user_events", type_="unique")
    op.create_unique_constraint(
        "_unique_user_events", "user_events", ["is_deleted", "id"]
    )
    op.drop_column("user_events", "event_id")
    op.drop_column("transfer_ownership", "applet_id")
    op.drop_column("user_events", "user_id")
    op.drop_constraint(
        op.f("fk_user_applet_accesses_user_id_users"),
        "user_applet_accesses",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_user_applet_accesses_applet_id_applets"),
        "user_applet_accesses",
        type_="foreignkey",
    )
    op.drop_index(
        op.f("ix_user_applet_accesses_user_id"),
        table_name="user_applet_accesses",
    )
    op.drop_index(
        op.f("ix_user_applet_accesses_applet_id"),
        table_name="user_applet_accesses",
    )
    op.drop_column("user_applet_accesses", "applet_id")
    op.drop_column("user_applet_accesses", "user_id")
    op.drop_constraint(
        op.f("fk_themes_creator_id_users"), "themes", type_="foreignkey"
    )
    op.drop_column("themes", "creator_id")
    op.drop_constraint(
        op.f("fk_reusable_item_choices_user_id_users"),
        "reusable_item_choices",
        type_="foreignkey",
    )
    op.drop_constraint(
        "_unique_item_choices", "reusable_item_choices", type_="unique"
    )
    op.create_unique_constraint(
        "_unique_item_choices",
        "reusable_item_choices",
        ["token_name", "token_value", "input_type"],
    )
    op.drop_column("reusable_item_choices", "user_id")
    op.drop_constraint(
        op.f("fk_invitations_invitor_id_users"),
        "invitations",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_invitations_applet_id_applets"),
        "invitations",
        type_="foreignkey",
    )
    op.drop_column("invitations", "invitor_id")
    op.drop_column("invitations", "applet_id")
    op.drop_constraint(
        op.f("fk_folders_creator_id_users"), "folders", type_="foreignkey"
    )
    op.drop_column("folders", "creator_id")
    op.add_column(
        "flows",
        sa.Column(
            "guid", postgresql.UUID(), autoincrement=False, nullable=True
        ),
    )
    op.drop_constraint(
        op.f("fk_flows_applet_id_applets"), "flows", type_="foreignkey"
    )
    op.drop_column("flows", "applet_id")
    op.drop_constraint(
        op.f("fk_flow_items_activity_flow_id_flows"),
        "flow_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_flow_items_activity_id_activities"),
        "flow_items",
        type_="foreignkey",
    )
    op.drop_column("flow_items", "activity_id")
    op.drop_column("flow_items", "activity_flow_id")
    op.alter_column(
        "flow_item_histories",
        "id",
        existing_type=postgresql.UUID(),
        nullable=False,
    )
    op.add_column(
        "flow_histories",
        sa.Column(
            "guid", postgresql.UUID(), autoincrement=False, nullable=True
        ),
    )
    op.alter_column(
        "flow_histories", "id", existing_type=postgresql.UUID(), nullable=False
    )
    op.drop_constraint(
        op.f("fk_flow_events_event_id_events"),
        "flow_events",
        type_="foreignkey",
    )
    op.drop_constraint("_unique_flow_events", "flow_events", type_="unique")
    op.create_unique_constraint(
        "_unique_flow_events",
        "flow_events",
        ["flow_id", "event_id", "is_deleted"],
    )
    op.drop_column("flow_events", "event_id")
    op.drop_column("flow_events", "flow_id")
    op.drop_constraint(
        op.f("fk_events_periodicity_id_periodicity"),
        "events",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_events_applet_id_applets"), "events", type_="foreignkey"
    )
    op.drop_column("events", "applet_id")
    op.drop_column("events", "periodicity_id")
    op.drop_constraint(
        op.f("fk_applets_creator_id_users"), "applets", type_="foreignkey"
    )
    op.drop_constraint(
        op.f("fk_applets_folder_id_folders"), "applets", type_="foreignkey"
    )
    op.drop_column("applets", "folder_id")
    op.drop_column("applets", "creator_id")
    op.drop_column("applets", "account_id")
    op.drop_column("applets", "theme_id")
    op.drop_constraint(
        op.f("fk_applet_histories_creator_id_users"),
        "applet_histories",
        type_="foreignkey",
    )
    op.alter_column(
        "applet_histories",
        "id",
        existing_type=postgresql.UUID(),
        nullable=False,
    )
    op.drop_column("applet_histories", "creator_id")
    op.drop_column("applet_histories", "account_id")
    op.drop_column("applet_histories", "theme_id")
    op.drop_constraint(
        op.f("fk_answers_flow_items_applet_id_applets"),
        "answers_flow_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_answers_flow_items_respondent_id_users"),
        "answers_flow_items",
        type_="foreignkey",
    )
    op.drop_column("answers_flow_items", "applet_id")
    op.drop_column("answers_flow_items", "respondent_id")
    op.drop_constraint(
        op.f("fk_answers_activity_items_respondent_id_users"),
        "answers_activity_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_answers_activity_items_applet_id_applets"),
        "answers_activity_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("fk_answers_activity_items_activity_id_activities"),
        "answers_activity_items",
        type_="foreignkey",
    )
    op.drop_column("answers_activity_items", "activity_id")
    op.drop_column("answers_activity_items", "applet_id")
    op.drop_column("answers_activity_items", "respondent_id")
    op.drop_constraint(
        op.f("fk_activity_items_activity_id_activities"),
        "activity_items",
        type_="foreignkey",
    )
    op.drop_column("activity_items", "activity_id")
    op.alter_column(
        "activity_item_histories",
        "id",
        existing_type=postgresql.UUID(),
        nullable=False,
    )
    op.alter_column(
        "activity_histories",
        "id",
        existing_type=postgresql.UUID(),
        nullable=False,
    )
    op.drop_constraint(
        op.f("fk_activity_events_event_id_events"),
        "activity_events",
        type_="foreignkey",
    )
    op.drop_column("activity_events", "event_id")
    op.drop_column("activity_events", "activity_id")
    op.drop_constraint(
        op.f("fk_activities_applet_id_applets"),
        "activities",
        type_="foreignkey",
    )
    op.drop_column("activities", "applet_id")
    # ### end Alembic commands ###
