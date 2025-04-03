import datetime
import traceback
import uuid
from itertools import groupby
from typing import cast

import typer
from pydantic import EmailStr, NonNegativeInt
from sqlalchemy import update
from sqlalchemy.cimmutabledict import immutabledict
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from apps.activities.domain.activity_create import ActivityCreate, ActivityItemCreate
from apps.activities.domain.response_type_config import MessageConfig, ResponseType
from apps.applets.commands.applet.seed.applet_config_file_v1 import (
    ActivityConfig,
    AlwaysAvailableEventConfig,
    AppletConfig,
    AppletConfigFileV1,
    EventConfig,
    UserConfig,
)
from apps.applets.commands.applet.seed.errors import (
    AppletActivityIdsAlreadyExistsError,
    AppletAlreadyExistsError,
    AppletNameAlreadyExistsError,
    EmailMismatchError,
    EventIdAlreadyExistsError,
    FirstNameMismatchError,
    LastNameMismatchError,
    PasswordMismatchError,
    SeedError,
    SeedUserIdMismatchError,
    SeedUserIsDeletedError,
    SubjectIdAlreadyExistsError,
)
from apps.applets.domain.applet_create_update import AppletCreate
from apps.applets.domain.applet_full import AppletFull
from apps.applets.domain.base import Encryption
from apps.applets.errors import AppletAlreadyExist, AppletNotFoundError
from apps.applets.service import AppletService
from apps.authentication.services import AuthenticationService
from apps.schedule.db.schemas import AppletEventsSchema, EventHistorySchema, EventSchema
from apps.schedule.domain.constants import EventType, PeriodicityType, TimerType
from apps.schedule.domain.schedule import (
    EventCreate,
    EventRequest,
    EventUpdateRequest,
    Notification,
    NotificationSettingRequest,
    PeriodicityRequest,
    PublicEvent,
    ReminderSettingRequest,
)
from apps.schedule.service import ScheduleService
from apps.subjects.db.schemas import SubjectSchema
from apps.subjects.domain import SubjectCreate
from apps.subjects.services import SubjectsService
from apps.users import User, UserIsDeletedError, UserNotFound, UserSchema
from apps.users.domain import UserCreate
from apps.users.services.user import UserService
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.database import atomic, session_manager


async def update_subject_details(
    session: AsyncSession, existing_subject_id: uuid.UUID, new_subject_data: tuple[uuid.UUID, datetime.datetime]
) -> None:
    query = update(SubjectSchema)
    query = query.where(SubjectSchema.id == existing_subject_id)

    values = {
        "id": new_subject_data[0],
        "created_at": new_subject_data[1],
    }

    query = query.values(**values)
    await session.execute(query, execution_options=immutabledict({"synchronize_session": False}))


async def create_and_update_new_event(
    session: AsyncSession,
    event: EventConfig,
    activity: ActivityConfig,
    applet_owner: User,
    applet: AppletFull,
):
    """
    Create a new event using the existing service method, and then manually update its properties (id, version,
    created_at)
    """
    schedule_service = ScheduleService(session, applet_owner.id)
    created_event = await schedule_service.create_schedule(
        EventRequest(
            start_time=event.start_time,
            end_time=event.end_time,
            access_before_schedule=getattr(event, "access_before_start_time", None),
            one_time_completion=getattr(event, "one_time_completion", None),
            respondent_id=event.user_id,
            activity_id=activity.id,
            flow_id=None,
            periodicity=PeriodicityRequest(
                type=event.periodicity.upper(),
                start_date=getattr(event, "start_date", None),
                end_date=getattr(event, "end_date", None),
                selected_date=getattr(event, "selected_date", None),
            ),
            notification=Notification(
                notifications=[
                    NotificationSettingRequest(
                        trigger_type=notification.trigger_type,
                        from_time=getattr(notification, "from_time", None),
                        to_time=getattr(notification, "to_time", None),
                        at_time=getattr(notification, "at_time", None),
                        order=i,
                    )
                    for i, notification in enumerate(event.notifications)
                ]
                if len(event.notifications) > 0
                else None,
                reminder=ReminderSettingRequest(
                    activity_incomplete=event.reminder.activity_incomplete,
                    reminder_time=event.reminder.reminder_time,
                )
                if event.reminder
                else None,
            )
            if len(event.notifications) > 0 or event.reminder
            else None,
            timer=None,
            timer_type=TimerType.NOT_SET,
        ),
        applet_id=applet.id,
    )

    try:
        # Now let's set the fields we couldn't in the create method (id, version, created_at)
        await update_first_event_version(
            session=session,
            existing_event=created_event,
            new_event_id=event.id,
            new_event_version=event.version,
            new_event_created_at=event.created_at,
            is_deleted=event.is_deleted,
        )
    except IntegrityError as e:
        raise EventIdAlreadyExistsError(event.id, activity.id) from e


async def update_first_event_version(
    session: AsyncSession,
    existing_event: PublicEvent,
    new_event_id: uuid.UUID,
    new_event_created_at: datetime.datetime,
    new_event_version: str,
    is_deleted: bool = False,
    event_data: EventCreate | None = None,
) -> None:
    """
    Update an event that may not have been created by this seed script. Entries already exist in the `events`,
    `event_histories`, and `applet_events` tables, and we manually update their properties. Which properties get
    updated is determined by the presence of the `event_data` parameter.
    """
    values: dict = {
        "id": new_event_id,
        "created_at": new_event_created_at,
        "updated_at": new_event_created_at,
        "version": new_event_version,
    }

    if event_data:
        values.update(
            {
                "start_time": event_data.start_time,
                "end_time": event_data.end_time,
                "timer": event_data.timer,
                "timer_type": event_data.timer_type,
                "periodicity": event_data.periodicity,
                "user_id": event_data.user_id,
                "activity_id": event_data.activity_id,
                "activity_flow_id": event_data.activity_flow_id,
                "event_type": event_data.event_type,
                "one_time_completion": getattr(event_data, "one_time_completion", None),
                "access_before_schedule": getattr(event_data, "access_before_schedule", None),
                "start_date": getattr(event_data, "start_date", None),
                "end_date": getattr(event_data, "end_date", None),
                "selected_date": getattr(event_data, "selected_date", None),
            }
        )

    # Update `events` table
    query = update(EventSchema)
    query = query.where(EventSchema.id == existing_event.id)
    query = query.values(**values)
    query = query.returning(EventSchema)
    db_result = await session.execute(query, execution_options=immutabledict({"synchronize_session": False}))
    mappings = db_result.mappings().all()
    updated_event = EventSchema(**mappings[0])

    existing_id_version = f"{existing_event.id}_{existing_event.version}"
    id_version = f"{updated_event.id}_{updated_event.version}"

    # Update `event_histories` table
    history_query = update(EventHistorySchema)
    history_query = history_query.where(EventHistorySchema.id_version == existing_id_version)

    history_values = {
        **values,
        "id_version": id_version,
        "is_deleted": is_deleted,
    }
    history_query = history_query.values(**history_values)
    await session.execute(history_query, execution_options=immutabledict({"synchronize_session": False}))

    # Update `applet_events` table
    applet_events_query = update(AppletEventsSchema)
    applet_events_query = applet_events_query.where(AppletEventsSchema.event_id == id_version)
    applet_events_query = applet_events_query.values(
        # This created_at column represents when either the event or the applet version was created
        # Since we currently only support one applet version, we can use the event's created_at
        created_at=new_event_created_at,
        updated_at=new_event_created_at,
    )
    await session.execute(applet_events_query, execution_options=immutabledict({"synchronize_session": False}))


async def update_subsequent_event_version(
    session: AsyncSession,
    applet: AppletFull,
    existing_event: PublicEvent,
    event_data: EventConfig,
):
    """
    Update an event that was created by this seed script, by creating a new version. We use the existing service
    method to update the `events` table, and create entries in `event_histories` and `applet_events`, after which
    we will manually update some of their properties
    """
    updated_schedule = await ScheduleService(session, applet.owner_id).update_schedule(
        applet_id=applet.id,
        schedule_id=existing_event.id,
        schedule=EventUpdateRequest(
            start_time=event_data.start_time,
            end_time=event_data.end_time,
            access_before_schedule=getattr(event_data, "access_before_start_time", None),
            one_time_completion=getattr(event_data, "one_time_completion", None),
            periodicity=PeriodicityRequest(
                type=event_data.periodicity.upper(),
                start_date=getattr(event_data, "start_date", None),
                end_date=getattr(event_data, "end_date", None),
                selected_date=getattr(event_data, "selected_date", None),
            ),
            notification=Notification(
                notifications=[
                    NotificationSettingRequest(
                        trigger_type=notification.trigger_type,
                        from_time=getattr(notification, "from_time", None),
                        to_time=getattr(notification, "to_time", None),
                        at_time=getattr(notification, "at_time", None),
                        order=i,
                    )
                    for i, notification in enumerate(event_data.notifications)
                ]
                if len(event_data.notifications) > 0
                else None,
                reminder=ReminderSettingRequest(
                    activity_incomplete=event_data.reminder.activity_incomplete,
                    reminder_time=event_data.reminder.reminder_time,
                )
                if event_data.reminder
                else None,
            )
            if len(event_data.notifications) > 0 or event_data.reminder
            else None,
            timer=None,
            timer_type=TimerType.NOT_SET,
        ),
    )

    values: dict = {
        "version": event_data.version,
        "updated_at": event_data.created_at,
    }

    # Update `events` table
    query = update(EventSchema)
    query = query.where(EventSchema.id == existing_event.id)
    query = query.values(**values)
    query = query.returning(EventSchema)
    db_result = await session.execute(query, execution_options=immutabledict({"synchronize_session": False}))
    updated_event = EventSchema(**db_result.mappings().all()[0])

    existing_id_version = f"{existing_event.id}_{updated_schedule.version}"
    id_version = f"{updated_event.id}_{updated_event.version}"

    # Update `event_histories` table
    history_query = update(EventHistorySchema)
    history_query = history_query.where(EventHistorySchema.id_version == existing_id_version)

    history_values = {
        "id_version": id_version,
        "version": event_data.version,
        "created_at": event_data.created_at,
        "updated_at": event_data.created_at,
        "is_deleted": event_data.is_deleted,
    }
    history_query = history_query.values(**history_values)
    await session.execute(history_query, execution_options=immutabledict({"synchronize_session": False}))

    # Update `applet_events` table
    applet_events_query = update(AppletEventsSchema)
    applet_events_query = applet_events_query.where(AppletEventsSchema.event_id == id_version)
    applet_events_query = applet_events_query.values(
        # This created_at column represents when either the event or the applet version was created
        # Since we currently only support one applet version, we can use the event's created_at
        created_at=event_data.created_at,
        updated_at=event_data.created_at,
    )
    await session.execute(applet_events_query, execution_options=immutabledict({"synchronize_session": False}))


async def create_users(session: AsyncSession, config_users: list[UserConfig]) -> list[User]:
    schema_users: list[User] = []
    user_service = UserService(session)
    auth_service = AuthenticationService(session)
    for user in config_users:
        schema_user: User | None = None
        try:
            schema_user = await user_service.get(user.id)
        except UserNotFound:
            try:
                schema_user = await user_service.get_by_email(user.email)
            except UserNotFound:
                pass
        except UserIsDeletedError as e:
            raise SeedUserIsDeletedError(user.id) from e

        if not schema_user:
            schema_user = await user_service.create_user(
                UserCreate(
                    email=EmailStr(user.email),
                    first_name=user.first_name,
                    last_name=user.last_name,
                    password=user.password,
                ),
                user.id,
            )

            # Create default workspace for new user
            await WorkspaceService(session, user.id).create_workspace_from_user(schema_user)

            update_query = update(UserSchema)
            update_query = update_query.where(UserSchema.id == schema_user.id)
            values = {
                "created_at": user.created_at,
            }

            update_query = update_query.values(**values)
            await session.execute(update_query, execution_options=immutabledict({"synchronize_session": False}))

        elif schema_user.id != user.id:
            raise SeedUserIdMismatchError(user.id)
        elif schema_user.email_encrypted != user.email:
            raise EmailMismatchError(user.id)
        elif schema_user.first_name != user.first_name:
            raise FirstNameMismatchError(user.id)
        elif schema_user.last_name != user.last_name:
            raise LastNameMismatchError(user.id)
        elif not auth_service.verify_password(user.password, schema_user.hashed_password, raise_exception=False):
            raise PasswordMismatchError(user.id)

        schema_users.append(schema_user)

    return schema_users


async def create_subjects(
    session: AsyncSession,
    applet: AppletConfig,
    applet_owner: User,
    schema_users: list[User],
):
    subject_service = SubjectsService(session, applet_owner.id)

    # Create the rest of the subjects
    for subject in applet.subjects:
        if "owner" in subject.roles:
            # The owner subject has already been created and updated
            continue
        else:
            pass
            subject_user = next((user for user in schema_users if user.id == subject.user_id), None)
            created_subject = await subject_service.create(
                SubjectCreate(
                    applet_id=applet.id,
                    email=subject_user.email if subject_user else None,
                    creator_id=applet_owner.id,
                    user_id=subject_user.id if subject_user else None,
                    language="en",
                    first_name=subject_user.first_name if subject_user else None,
                    last_name=subject_user.last_name if subject_user else None,
                    secret_user_id=subject.secret_user_id,
                    nickname=subject.nickname,
                    tag=subject.tag,
                )
            )

            try:
                await update_subject_details(
                    session,
                    created_subject.id,
                    (subject.id, subject.created_at),
                )
            except IntegrityError as e:
                raise SubjectIdAlreadyExistsError(subject.id, applet.id) from e


async def create_activity(
    session: AsyncSession,
    activity: ActivityConfig,
    applet_owner: User,
    applet: AppletFull,
):
    schedule_service = ScheduleService(session, applet_owner.id)

    applet_schedules = await schedule_service.get_all_schedules(applet.id)

    events: list[EventConfig] = activity.events
    for group_idx, [_, grouped_events] in enumerate(groupby(events, lambda ev: ev.id)):
        for version_idx, event in enumerate(grouped_events):
            if version_idx == 0:
                if group_idx == 0:
                    # This is the first event version in the first group, which makes it the default, auto-created
                    # always available event for this activity. We need to update instead of create
                    always_available_event = cast(AlwaysAvailableEventConfig, event)
                    existing_always_available_event = next(
                        (e for e in applet_schedules if e.activity_id == activity.id),
                        None,
                    )
                    if (
                        not existing_always_available_event
                        or existing_always_available_event.periodicity.type != PeriodicityType.ALWAYS
                    ):
                        raise RuntimeError(
                            f"Unexpected error: No default always available event found for activity {activity.id}"
                        )

                    event_data = EventCreate(
                        applet_id=applet.id,
                        start_time=event.start_time,
                        end_time=event.end_time,
                        access_before_schedule=None,
                        timer=None,
                        timer_type=TimerType.NOT_SET,
                        one_time_completion=always_available_event.one_time_completion,
                        periodicity=PeriodicityType.ALWAYS,
                        start_date=None,
                        end_date=None,
                        selected_date=None,
                        user_id=event.user_id,
                        activity_id=activity.id,
                        activity_flow_id=None,
                        event_type=EventType.ACTIVITY,
                    )

                    # Update the always available event to match the details specified in the config
                    try:
                        await update_first_event_version(
                            session,
                            existing_event=existing_always_available_event,
                            new_event_id=always_available_event.id,
                            new_event_version=always_available_event.version,
                            new_event_created_at=always_available_event.created_at,
                            is_deleted=event.is_deleted,
                            event_data=event_data,
                        )
                    except IntegrityError as e:
                        raise EventIdAlreadyExistsError(event.id, activity.id) from e
                else:
                    # This is the first event version, but not the first group. It must be created before updating
                    await create_and_update_new_event(
                        session=session,
                        event=event,
                        activity=activity,
                        applet_owner=applet_owner,
                        applet=applet,
                    )
            else:
                existing_event = await schedule_service.get_schedule_by_id(event.id, applet.id)
                # This is not the first version of this event. It should be updated
                await update_subsequent_event_version(
                    session=session,
                    applet=applet,
                    existing_event=existing_event,
                    event_data=event,
                )


async def seed_applet_v1(config: AppletConfigFileV1, from_cli: bool = False) -> None:
    typer.echo("Seeding data from v1 config file...")
    s_maker = session_manager.get_session()
    try:
        async with s_maker() as session:
            async with atomic(session):
                schema_users: list[User] = await create_users(session, config.users)

                for applet in config.applets:
                    applet_owner_subject = next(subject for subject in applet.subjects if "owner" in subject.roles)
                    applet_owner = await UserService(session).get(applet.encryption.account_id)

                    if not applet_owner:
                        # TODO: Change to SeedError subclass
                        raise RuntimeError(
                            f"Unexpected Error: Applet owner {applet_owner_subject.user_id} not found in the database."
                        )

                    applet_service = AppletService(session, applet_owner.id)

                    # Ensure the applet does not exist before creating it
                    try:
                        await applet_service.exist_by_id(applet.id)
                        raise AppletAlreadyExistsError(applet.id)
                    except AppletNotFoundError:
                        pass

                    try:
                        await applet_service._validate_applet_name(applet.display_name)
                    except AppletAlreadyExist as e:
                        raise AppletNameAlreadyExistsError(applet.display_name) from e

                    encryption = Encryption(
                        public_key=applet.encryption.public_key,
                        prime=applet.encryption.prime,
                        base=applet.encryption.base,
                        account_id=str(applet_owner.id),
                    )

                    create_data = AppletCreate(
                        display_name=applet.display_name,
                        description={"en": applet.description},
                        link=None,
                        require_login=True,
                        pinned_at=None,
                        retention_period=None,
                        retention_type=None,
                        stream_enabled=None,
                        stream_ip_address=None,
                        stream_port=None,
                        encryption=encryption,
                        activities=[],
                        activity_flows=[],
                    )
                    create_data.__dict__["created_at"] = applet.created_at

                    for activity in applet.activities:
                        activity_create = ActivityCreate(
                            key=uuid.uuid4(),
                            name=activity.name,
                            description={"en": activity.description},
                            is_hidden=activity.is_hidden,
                            auto_assign=activity.auto_assign,
                            items=[],
                        )
                        activity_create.__dict__["id"] = activity.id
                        activity_create.__dict__["created_at"] = activity.created_at

                        item = ActivityItemCreate(
                            name="Message",
                            response_type=ResponseType.MESSAGE,
                            question={"en": "Message"},
                            config=MessageConfig(
                                type=ResponseType.MESSAGE,
                                remove_back_button=False,
                                timer=NonNegativeInt(0),
                            ),
                            response_values=None,
                        )
                        item.__dict__["created_at"] = activity.created_at
                        activity_create.items.append(item)
                        create_data.activities.append(activity_create)

                    if applet.report_server:
                        report_server = applet.report_server
                        create_data.report_server_ip = report_server.ip_address
                        create_data.report_public_key = report_server.public_key
                        create_data.report_recipients = report_server.recipients
                        create_data.report_include_user_id = report_server.include_user_id
                        create_data.report_include_case_id = report_server.include_case_id
                        create_data.report_email_body = report_server.email_body

                    try:
                        created_applet = await applet_service.create(
                            create_data=create_data,
                            manager_id=applet_owner.id,
                            manager_role=Role.OWNER,
                            applet_id=applet.id,
                        )
                    except IntegrityError as e:
                        raise AppletActivityIdsAlreadyExistsError(applet.id) from e

                    subject_service = SubjectsService(session, applet_owner.id)

                    # Update the subject ID of the owner subject
                    existing_owner_subject = await subject_service.get_by_user_and_applet(
                        user_id=applet_owner.id, applet_id=applet.id
                    )

                    if not existing_owner_subject:
                        raise RuntimeError(f"Unexpected Error: Owner subject {applet_owner_subject.id} not found.")

                    try:
                        await update_subject_details(
                            session,
                            existing_owner_subject.id,
                            (applet_owner_subject.id, applet_owner_subject.created_at),
                        )
                    except IntegrityError as e:
                        raise SubjectIdAlreadyExistsError(applet_owner_subject.id, applet.id) from e

                    # Create the rest of the subjects
                    await create_subjects(
                        session=session,
                        applet=applet,
                        applet_owner=applet_owner,
                        schema_users=schema_users,
                    )

                    # Create/update the events
                    for activity in applet.activities:
                        await create_activity(
                            session=session,
                            activity=activity,
                            applet_owner=applet_owner,
                            applet=created_applet,
                        )
    except Exception as e:
        if not from_cli:
            raise e
        elif isinstance(e, SeedError):
            typer.echo(typer.style(f"ERROR: {str(e)}", fg=typer.colors.RED))
        else:
            traceback.print_exc()
