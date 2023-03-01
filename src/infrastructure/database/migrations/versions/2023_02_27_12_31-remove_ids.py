"""remove ids

Revision ID: 8f62ff76eba0
Revises: 5a856165fb8d
Create Date: 2023-02-27 12:31:47.406056

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "8f62ff76eba0"
down_revision = "05cd246d924f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add pk(uuid) column
    op.add_column(
        "activities",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "transfer_ownership",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "activity_events",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "activity_histories",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "activity_item_histories",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "activity_items",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "answers_activity_items",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "answers_flow_items",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "applets",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "applet_histories",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "flow_events",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "flow_histories",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "flow_item_histories",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "flow_items",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "flows",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "folders",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "invitations",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "notification_logs",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "periodicity",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "reusable_item_choices",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "themes",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "user_applet_accesses",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "user_events",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "pk",
            postgresql.UUID(),
            nullable=False,
        ),
    )

    # Clear tables
    op.execute("""delete from activities;""")
    op.execute("""delete from transfer_ownership;""")
    op.execute("""delete from activity_events;""")
    op.execute("""delete from activity_histories;""")
    op.execute("""delete from activity_item_histories;""")
    op.execute("""delete from activity_items;""")
    op.execute("""delete from answers_activity_items;""")
    op.execute("""delete from answers_flow_items;""")
    op.execute("""delete from applets;""")
    op.execute("""delete from events;""")
    op.execute("""delete from applet_histories;""")
    op.execute("""delete from flow_events;""")
    op.execute("""delete from flow_histories;""")
    op.execute("""delete from flow_item_histories;""")
    op.execute("""delete from flow_items;""")
    op.execute("""delete from flows;""")
    op.execute("""delete from folders;""")
    op.execute("""delete from invitations;""")
    op.execute("""delete from notification_logs;""")
    op.execute("""delete from periodicity;""")
    op.execute("""delete from reusable_item_choices;""")
    op.execute("""delete from themes;""")
    op.execute("""delete from user_applet_accesses;""")
    op.execute("""delete from user_events;""")
    op.execute("""delete from users;""")

    # Drop column pk
    op.drop_constraint(
        "fk_activities_applet_id_applets",
        "activities",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_transfer_ownership_applet_id_applets",
        "transfer_ownership",
        type_="foreignkey",
    )
    op.drop_constraint(
        "_unique_activity_events",
        "activity_events",
        type_="unique",
    )
    op.create_unique_constraint(
        "_unique_activity_events",
        "activity_events",
        ["is_deleted"],
    )
    op.drop_constraint(
        "fk_activity_events_event_id_events",
        "activity_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_activity_items_activity_id_activities",
        "activity_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_answers_activity_items_applet_id_applets",
        "answers_activity_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_answers_activity_items_respondent_id_users",
        "answers_activity_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_answers_activity_items_activity_id_activities",
        "answers_activity_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_answers_flow_items_respondent_id_users",
        "answers_flow_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_answers_flow_items_applet_id_applets",
        "answers_flow_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_applet_histories_creator_id_users",
        "applet_histories",
        type_="foreignkey",
    )
    op.drop_constraint(
        "applet_creator_id",
        "applets",
        type_="foreignkey",
    )
    op.drop_constraint(
        "applets_folder",
        "applets",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_events_applet_id_applets",
        "events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_events_periodicity_id_periodicity",
        "events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "_unique_flow_events",
        "flow_events",
        type_="unique",
    )
    op.create_unique_constraint(
        "_unique_flow_events",
        "flow_events",
        ["is_deleted"],
    )
    op.drop_constraint(
        "fk_flow_events_event_id_events",
        "flow_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_flow_items_activity_flow_id_flows",
        "flow_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "flow_activity_id",
        "flow_items",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_flows_applet_id_applets",
        "flows",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_folders_creator_id_users",
        "folders",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_invitations_applet_id_applets",
        "invitations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_invitations_invitor_id_users",
        "invitations",
        type_="foreignkey",
    )
    op.drop_constraint(
        "_unique_item_choices",
        "reusable_item_choices",
        type_="unique",
    )
    op.create_unique_constraint(
        "_unique_item_choices",
        "reusable_item_choices",
        [
            "token_name",
            "token_value",
            "input_type",
        ],
    )
    op.drop_constraint(
        "fk_reusable_item_choices_user_id_users",
        "reusable_item_choices",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_themes_creator_users",
        "themes",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_user_applet_accesses_applet_id",
        table_name="user_applet_accesses",
    )
    op.drop_index(
        "ix_user_applet_accesses_user_id",
        table_name="user_applet_accesses",
    )
    op.drop_constraint(
        "fk_user_applet_accesses_user_id_users",
        "user_applet_accesses",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_user_applet_accesses_applet_id_applets",
        "user_applet_accesses",
        type_="foreignkey",
    )
    op.drop_constraint(
        "_unique_user_events",
        "user_events",
        type_="unique",
    )
    op.create_unique_constraint(
        "_unique_user_events",
        "user_events",
        ["is_deleted"],
    )
    op.drop_constraint(
        "fk_user_events_event_id_events",
        "user_events",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_user_events_user_id_users",
        "user_events",
        type_="foreignkey",
    )

    op.drop_column("activities", "applet_id")
    op.drop_column("transfer_ownership", "id")
    op.drop_column("transfer_ownership", "applet_id")
    op.drop_column("activity_histories", "id")
    op.drop_column("activity_item_histories", "id")
    op.drop_column("applet_histories", "id")
    op.drop_column("flow_histories", "id")
    op.drop_column("flow_item_histories", "id")
    op.drop_column("activities", "id")
    op.drop_column("activity_events", "id")
    op.drop_column("activity_events", "event_id")
    op.drop_column("activity_events", "activity_id")
    op.drop_column("activity_items", "id")
    op.drop_column("activity_items", "activity_id")
    op.drop_column("answers_activity_items", "applet_id")
    op.drop_column("answers_activity_items", "id")
    op.drop_column("answers_activity_items", "activity_id")
    op.drop_column("answers_activity_items", "respondent_id")
    op.drop_column("answers_flow_items", "applet_id")
    op.drop_column("answers_flow_items", "id")
    op.drop_column("answers_flow_items", "respondent_id")
    op.drop_column("applet_histories", "theme_id")
    op.drop_column("applet_histories", "creator_id")
    op.drop_column("applet_histories", "account_id")
    op.drop_column("applets", "folder_id")
    op.drop_column("applets", "theme_id")
    op.drop_column("applets", "creator_id")
    op.drop_column("applets", "id")
    op.drop_column("applets", "account_id")
    op.drop_column("events", "applet_id")
    op.drop_column("events", "id")
    op.drop_column("events", "periodicity_id")
    op.drop_column("flow_events", "id")
    op.drop_column("flow_events", "event_id")
    op.drop_column("flow_events", "flow_id")
    op.drop_column("flow_items", "id")
    op.drop_column("flow_items", "activity_id")
    op.drop_column("flow_items", "activity_flow_id")
    op.drop_column("flows", "applet_id")
    op.drop_column("flows", "id")
    op.drop_column("folders", "id")
    op.drop_column("folders", "creator_id")
    op.drop_column("invitations", "applet_id")
    op.drop_column("invitations", "id")
    op.drop_column("invitations", "invitor_id")
    op.drop_column("notification_logs", "id")
    op.drop_column("periodicity", "id")
    op.drop_column("reusable_item_choices", "id")
    op.drop_column("reusable_item_choices", "user_id")
    op.drop_column("themes", "id")
    op.drop_column("themes", "creator")
    op.drop_column("user_applet_accesses", "id")
    op.drop_column("user_applet_accesses", "user_id")
    op.drop_column("user_applet_accesses", "applet_id")
    op.drop_column("user_events", "id")
    op.drop_column("user_events", "event_id")
    op.drop_column("user_events", "user_id")
    op.drop_column("users", "id")

    # Change
    op.execute("""alter table activities rename column pk to id;""")
    op.execute("""alter table transfer_ownership rename column pk to id;""")
    op.execute("""alter table activity_events rename column pk to id;""")
    op.execute("""alter table activity_histories rename column pk to id;""")
    op.execute("""alter table activity_item_histories rename column pk to id;""")
    op.execute("""alter table activity_items rename column pk to id;""")
    op.execute("""alter table answers_activity_items rename column pk to id;""")
    op.execute("""alter table answers_flow_items rename column pk to id;""")
    op.execute("""alter table applets rename column pk to id;""")
    op.execute("""alter table events rename column pk to id;""")
    op.execute("""alter table applet_histories rename column pk to id;""")
    op.execute("""alter table flow_events rename column pk to id;""")
    op.execute("""alter table flow_histories rename column pk to id;""")
    op.execute("""alter table flow_item_histories rename column pk to id;""")
    op.execute("""alter table flow_items rename column pk to id;""")
    op.execute("""alter table flows rename column pk to id;""")
    op.execute("""alter table folders rename column pk to id;""")
    op.execute("""alter table invitations rename column pk to id;""")
    op.execute("""alter table notification_logs rename column pk to id;""")
    op.execute("""alter table periodicity rename column pk to id;""")
    op.execute("""alter table reusable_item_choices rename column pk to id;""")
    op.execute("""alter table themes rename column pk to id;""")
    op.execute("""alter table user_applet_accesses rename column pk to id;""")
    op.execute("""alter table user_events rename column pk to id;""")
    op.execute("""alter table users rename column pk to id;""")

    # Create primary key
    op.create_primary_key("pk_activities", "activities", ["id"])
    op.create_primary_key("pk_transfer_ownership", "transfer_ownership", ["id"])
    op.create_primary_key("pk_activity_events", "activity_events", ["id"])
    op.create_primary_key("pk_activity_items", "activity_items", ["id"])
    op.create_primary_key("pk_answers_activity_items", "answers_activity_items", ["id"])
    op.create_primary_key("pk_answers_flow_items", "answers_flow_items", ["id"])
    op.create_primary_key("pk_applets", "applets", ["id"])
    op.create_primary_key("pk_events", "events", ["id"])
    op.create_primary_key("pk_flow_events", "flow_events", ["id"])
    op.create_primary_key("pk_flow_items", "flow_items", ["id"])
    op.create_primary_key("pk_flows", "flows", ["id"])
    op.create_primary_key("pk_folders", "folders", ["id"])
    op.create_primary_key("pk_invitations", "invitations", ["id"])
    op.create_primary_key("pk_notification_logs", "notification_logs", ["id"])
    op.create_primary_key("pk_periodicity", "periodicity", ["id"])
    op.create_primary_key("pk_reusable_item_choices", "reusable_item_choices", ["id"])
    op.create_primary_key("pk_themes", "themes", ["id"])
    op.create_primary_key("pk_user_applet_accesses", "user_applet_accesses", ["id"])
    op.create_primary_key("pk_user_events", "user_events", ["id"])
    op.create_primary_key("pk_users", "users", ["id"])


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    # Drop primary key
    op.drop_constraint("pk_activities", "activities")
    op.drop_constraint("pk_transfer_ownership", "transfer_ownership")
    op.drop_constraint("pk_activity_events", "activity_events")
    op.drop_constraint("pk_activity_items", "activity_items")
    op.drop_constraint("pk_answers_activity_items", "answers_activity_items")
    op.drop_constraint("pk_answers_flow_items", "answers_flow_items")
    op.drop_constraint("pk_applets", "applets")
    op.drop_constraint("pk_events", "events")
    op.drop_constraint("pk_flow_events", "flow_events")
    op.drop_constraint("pk_flow_items", "flow_items")
    op.drop_constraint("pk_flows", "flows")
    op.drop_constraint("pk_folders", "folders")
    op.drop_constraint("pk_invitations", "invitations")
    op.drop_constraint("pk_notification_logs", "notification_logs")
    op.drop_constraint("pk_periodicity", "periodicity")
    op.drop_constraint("pk_reusable_item_choices", "reusable_item_choices")
    op.drop_constraint("pk_themes", "themes")
    op.drop_constraint("pk_user_applet_accesses", "user_applet_accesses")
    op.drop_constraint("pk_user_events", "user_events")
    op.drop_constraint("pk_users", "users")

    # Change
    op.execute("""alter table activities rename column id to pk;""")
    op.execute("""alter table transfer_ownership rename column id to pk;""")
    op.execute("""alter table activity_events rename column id to pk;""")
    op.execute("""alter table activity_histories rename column id to pk;""")
    op.execute("""alter table activity_item_histories rename column id to pk;""")
    op.execute("""alter table activity_items rename column id to pk;""")
    op.execute("""alter table answers_activity_items rename column id to pk;""")
    op.execute("""alter table answers_flow_items rename column id to pk;""")
    op.execute("""alter table applets rename column id to pk;""")
    op.execute("""alter table events rename column id to pk;""")
    op.execute("""alter table applet_histories rename column id to pk;""")
    op.execute("""alter table flow_events rename column id to pk;""")
    op.execute("""alter table flow_histories rename column id to pk;""")
    op.execute("""alter table flow_item_histories rename column id to pk;""")
    op.execute("""alter table flow_items rename column id to pk;""")
    op.execute("""alter table flows rename column id to pk;""")
    op.execute("""alter table folders rename column id to pk;""")
    op.execute("""alter table invitations rename column id to pk;""")
    op.execute("""alter table notification_logs rename column id to pk;""")
    op.execute("""alter table periodicity rename column id to pk;""")
    op.execute("""alter table reusable_item_choices rename column id to pk;""")
    op.execute("""alter table themes rename column id to pk;""")
    op.execute("""alter table user_applet_accesses rename column id to pk;""")
    op.execute("""alter table user_events rename column id to pk;""")
    op.execute("""alter table users rename column id to pk;""")

    op.execute("""create sequence if not exists users_id_seq""")
    op.execute("""create sequence if not exists transfer_ownership_id_seq""")
    op.execute("""create sequence if not exists user_events_id_seq""")
    op.execute("""create sequence if not exists user_applet_accesses_id_seq""")
    op.execute("""create sequence if not exists themes_id_seq""")
    op.execute("""create sequence if not exists reusable_item_choices_id_seq""")
    op.execute("""create sequence if not exists periodicity_id_seq""")
    op.execute("""create sequence if not exists notification_logs_id_seq""")
    op.execute("""create sequence if not exists invitations_id_seq""")
    op.execute("""create sequence if not exists folders_id_seq""")
    op.execute("""create sequence if not exists flows_id_seq""")
    op.execute("""create sequence if not exists flow_items_id_seq""")
    op.execute("""create sequence if not exists flow_events_id_seq""")
    op.execute("""create sequence if not exists events_id_seq""")
    op.execute("""create sequence if not exists applets_id_seq""")
    op.execute("""create sequence if not exists answers_flow_items_id_seq""")
    op.execute("""create sequence if not exists answers_activity_items_id_seq""")
    op.execute("""create sequence if not exists activity_items_id_seq""")
    op.execute("""create sequence if not exists activity_events_id_seq""")
    op.execute("""create sequence if not exists activities_id_seq""")

    op.add_column(
        "users",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('users_id_seq'::regclass)"),
            nullable=False,
        ),
    )
    op.add_column(
        "transfer_ownership",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('transfer_ownership_id_seq'::regclass)"),
            nullable=False,
        ),
    )
    op.add_column(
        "transfer_ownership",
        sa.Column(
            "applet_id",
            sa.INTEGER(),
            autoincrement=True,
            nullable=True,
        ),
    )
    op.add_column(
        "user_events",
        sa.Column(
            "user_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "user_events",
        sa.Column(
            "event_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "user_events",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('user_events_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.drop_constraint(
        "_unique_user_events",
        "user_events",
        type_="unique",
    )
    op.create_unique_constraint(
        "_unique_user_events",
        "user_events",
        ["user_id", "event_id", "is_deleted"],
    )
    op.add_column(
        "user_applet_accesses",
        sa.Column(
            "applet_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "user_applet_accesses",
        sa.Column(
            "user_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "user_applet_accesses",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('user_applet_accesses_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_user_applet_accesses_user_id",
        "user_applet_accesses",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_applet_accesses_applet_id",
        "user_applet_accesses",
        ["applet_id"],
        unique=False,
    )
    op.add_column(
        "themes",
        sa.Column(
            "creator",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "themes",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('themes_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.add_column(
        "reusable_item_choices",
        sa.Column(
            "user_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "reusable_item_choices",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('reusable_item_choices_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.drop_constraint(
        "_unique_item_choices",
        "reusable_item_choices",
        type_="unique",
    )
    op.create_unique_constraint(
        "_unique_item_choices",
        "reusable_item_choices",
        [
            "user_id",
            "token_name",
            "token_value",
            "input_type",
        ],
    )
    op.add_column(
        "periodicity",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('periodicity_id_seq'::regclass)"),
            nullable=False,
        ),
    )
    op.add_column(
        "notification_logs",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('notification_logs_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.add_column(
        "invitations",
        sa.Column(
            "invitor_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "invitations",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('invitations_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.add_column(
        "invitations",
        sa.Column(
            "applet_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "folders",
        sa.Column(
            "creator_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "folders",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('folders_id_seq'::regclass)"),
            nullable=False,
        ),
    )
    op.add_column(
        "flows",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('flows_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.add_column(
        "flows",
        sa.Column(
            "applet_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "flow_items",
        sa.Column(
            "activity_flow_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "flow_items",
        sa.Column(
            "activity_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "flow_items",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('flow_items_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.add_column(
        "flow_events",
        sa.Column(
            "flow_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "flow_events",
        sa.Column(
            "event_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "flow_events",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('flow_events_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    # op.drop_constraint(
    #     "_unique_flow_events",
    #     "flow_events",
    #     type_="unique",
    # )
    op.create_unique_constraint(
        "_unique_flow_events",
        "flow_events",
        ["flow_id", "event_id", "is_deleted"],
    )
    op.add_column(
        "events",
        sa.Column(
            "periodicity_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('events_id_seq'::regclass)"),
            nullable=False,
        ),
    )
    op.add_column(
        "events",
        sa.Column(
            "applet_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "applets",
        sa.Column(
            "account_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "applets",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('applets_id_seq'::regclass)"),
            nullable=False,
        ),
    )
    op.add_column(
        "applets",
        sa.Column(
            "creator_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "applets",
        sa.Column(
            "theme_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "applets",
        sa.Column(
            "folder_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "applet_histories",
        sa.Column(
            "account_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "applet_histories",
        sa.Column(
            "creator_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "applet_histories",
        sa.Column(
            "theme_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "answers_flow_items",
        sa.Column(
            "respondent_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "answers_flow_items",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('answers_flow_items_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.add_column(
        "answers_flow_items",
        sa.Column(
            "applet_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "answers_activity_items",
        sa.Column(
            "respondent_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "answers_activity_items",
        sa.Column(
            "activity_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "answers_activity_items",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('answers_activity_items_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.add_column(
        "answers_activity_items",
        sa.Column(
            "applet_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "activity_items",
        sa.Column(
            "activity_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "activity_items",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('activity_items_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.add_column(
        "activity_events",
        sa.Column(
            "activity_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "activity_events",
        sa.Column(
            "event_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "activity_events",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('activity_events_id_seq'::regclass)"),
            nullable=True,
        ),
    )
    op.create_unique_constraint(
        "_unique_activity_events",
        "activity_events",
        ["activity_id", "event_id", "is_deleted"],
    )
    op.add_column(
        "activities",
        sa.Column(
            "id",
            sa.INTEGER(),
            autoincrement=True,
            server_default=sa.text("nextval('activities_id_seq'::regclass)"),
            nullable=False,
        ),
    )
    op.add_column(
        "activities",
        sa.Column(
            "applet_id",
            sa.INTEGER(),
            autoincrement=False,
            nullable=True,
        ),
    )

    # Create primary key
    op.create_primary_key("pk_activities", "activities", ["id"])
    op.create_primary_key("pk_activity_events", "activity_events", ["id"])
    op.create_primary_key("pk_activity_items", "activity_items", ["id"])
    op.create_primary_key("pk_answers_activity_items", "answers_activity_items", ["id"])
    op.create_primary_key("pk_answers_flow_items", "answers_flow_items", ["id"])
    op.create_primary_key("pk_applets", "applets", ["id"])
    op.create_primary_key("pk_events", "events", ["id"])
    op.create_primary_key("pk_flow_events", "flow_events", ["id"])
    op.create_primary_key("pk_flow_items", "flow_items", ["id"])
    op.create_primary_key("pk_flows", "flows", ["id"])
    op.create_primary_key("pk_folders", "folders", ["id"])
    op.create_primary_key("pk_invitations", "invitations", ["id"])
    op.create_primary_key("pk_notification_logs", "notification_logs", ["id"])
    op.create_primary_key("pk_periodicity", "periodicity", ["id"])
    op.create_primary_key("pk_reusable_item_choices", "reusable_item_choices", ["id"])
    op.create_primary_key("pk_themes", "themes", ["id"])
    op.create_primary_key("pk_user_applet_accesses", "user_applet_accesses", ["id"])
    op.create_primary_key("pk_user_events", "user_events", ["id"])
    op.create_primary_key("pk_users", "users", ["id"])

    op.create_foreign_key(
        "fk_user_events_user_id_users",
        "user_events",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_user_events_event_id_events",
        "user_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_user_applet_accesses_applet_id_applets",
        "user_applet_accesses",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_user_applet_accesses_user_id_users",
        "user_applet_accesses",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_themes_creator_users",
        "themes",
        "users",
        ["creator"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_reusable_item_choices_user_id_users",
        "reusable_item_choices",
        "users",
        ["user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_invitations_invitor_id_users",
        "invitations",
        "users",
        ["invitor_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_invitations_applet_id_applets",
        "invitations",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_transfer_ownership_applet_id_applets",
        "transfer_ownership",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_folders_creator_id_users",
        "folders",
        "users",
        ["creator_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_flows_applet_id_applets",
        "flows",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "flow_activity_id",
        "flow_items",
        "activities",
        ["activity_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_flow_items_activity_flow_id_flows",
        "flow_items",
        "flows",
        ["activity_flow_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_flow_events_event_id_events",
        "flow_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_events_periodicity_id_periodicity",
        "events",
        "periodicity",
        ["periodicity_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_events_applet_id_applets",
        "events",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "applets_folder",
        "applets",
        "folders",
        ["folder_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "applet_creator_id",
        "applets",
        "users",
        ["creator_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_applet_histories_creator_id_users",
        "applet_histories",
        "users",
        ["creator_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_answers_flow_items_applet_id_applets",
        "answers_flow_items",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_answers_flow_items_respondent_id_users",
        "answers_flow_items",
        "users",
        ["respondent_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_answers_activity_items_activity_id_activities",
        "answers_activity_items",
        "activities",
        ["activity_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_answers_activity_items_respondent_id_users",
        "answers_activity_items",
        "users",
        ["respondent_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_answers_activity_items_applet_id_applets",
        "answers_activity_items",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_activity_items_activity_id_activities",
        "activity_items",
        "activities",
        ["activity_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_activity_events_event_id_events",
        "activity_events",
        "events",
        ["event_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_activities_applet_id_applets",
        "activities",
        "applets",
        ["applet_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_column("users", "pk")
    op.drop_column("transfer_ownership", "pk")
    op.drop_column("user_events", "pk")
    op.drop_column("user_applet_accesses", "pk")
    op.drop_column("themes", "pk")
    op.drop_column("reusable_item_choices", "pk")
    op.drop_column("periodicity", "pk")
    op.drop_column("notification_logs", "pk")
    op.drop_column("invitations", "pk")
    op.drop_column("folders", "pk")
    op.drop_column("flows", "pk")
    op.drop_column("flow_items", "pk")
    op.drop_column("flow_item_histories", "pk")
    op.drop_column("flow_histories", "pk")
    op.drop_column("flow_events", "pk")
    op.drop_column("events", "pk")
    op.drop_column("applets", "pk")
    op.drop_column("applet_histories", "pk")
    op.drop_column("answers_flow_items", "pk")
    op.drop_column("answers_activity_items", "pk")
    op.drop_column("activity_items", "pk")
    op.drop_column("activity_item_histories", "pk")
    op.drop_column("activity_histories", "pk")
    op.drop_column("activity_events", "pk")
    op.drop_column("activities", "pk")
    # ### end Alembic commands ###
