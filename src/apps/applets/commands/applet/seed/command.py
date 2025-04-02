import datetime
import traceback
import uuid
from itertools import groupby

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
from apps.applets.domain.base import Encryption
from apps.applets.errors import AppletAlreadyExist, AppletNotFoundError
from apps.applets.service import AppletService
from apps.authentication.services import AuthenticationService
from apps.schedule.db.schemas import EventHistorySchema, EventSchema
from apps.schedule.domain.constants import EventType, TimerType
from apps.schedule.domain.schedule import (
    EventCreate,
    EventRequest,
    Notification,
    NotificationSettingRequest,
    PeriodicityRequest,
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


async def update_event_details(
    session: AsyncSession,
    existing_event_id: uuid.UUID,
    new_event_id: uuid.UUID,
    new_event_created_at: datetime.datetime | None = None,
    new_event_version: str | None = None,
    event_data: EventCreate | None = None,
    include_history: bool = False,
) -> None:
    values: dict = {
        "id": new_event_id,
    }

    if new_event_created_at:
        values["created_at"] = new_event_created_at

    if new_event_version:
        values["version"] = new_event_version

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
            }
        )
        if hasattr(event_data, "one_time_completion"):
            values["one_time_completion"] = event_data.one_time_completion
            if hasattr(event_data, "access_before_schedule"):
                values["access_before_schedule"] = event_data.access_before_schedule
            if hasattr(event_data, "start_date"):
                values["start_date"] = event_data.start_date
            if hasattr(event_data, "end_date"):
                values["end_date"] = event_data.end_date
            if hasattr(event_data, "selected_date"):
                values["selected_date"] = event_data.selected_date

    query = update(EventSchema)
    query = query.where(EventSchema.id == existing_event_id)
    query = query.values(**values)
    query = query.returning(EventSchema)
    db_result = await session.execute(query, execution_options=immutabledict({"synchronize_session": False}))
    updated_event = EventSchema(**db_result.mappings().all()[0])

    if include_history:
        history_query = update(EventHistorySchema)
        history_query = history_query.where(EventHistorySchema.id == existing_event_id)
        history_values = {
            **values,
            "id_version": f"{updated_event.id}_{updated_event.version}",
        }
        history_query = history_query.values(**history_values)
        await session.execute(history_query, execution_options=immutabledict({"synchronize_session": False}))


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
    applet: AppletConfig,
):
    schedule_service = ScheduleService(session, applet_owner.id)

    applet_schedules = await schedule_service.get_all_schedules(applet.id)

    default_always_available_event_created = False
    events: list[EventConfig] = activity.events
    for id, grouped_events in groupby(events, lambda ev: ev.id):
        for i, event in enumerate(grouped_events):
            # First event in this series
            if i == 0:
                existing_always_available_event = next(
                    (e for e in applet_schedules if e.activity_id == activity.id),
                    None,
                )
                if not existing_always_available_event:
                    raise RuntimeError(f"Unexpected error: No existing event found for activity {activity.id}")

                try:
                    await update_event_details(
                        session,
                        existing_event_id=existing_always_available_event.id,
                        new_event_id=event.id
                        if not default_always_available_event_created
                        else existing_always_available_event.id,
                        new_event_version=event.version
                        if not default_always_available_event_created
                        else existing_always_available_event.version,
                        new_event_created_at=event.created_at if not default_always_available_event_created else None,
                        event_data=EventCreate(
                            applet_id=applet.id,
                            start_time=event.start_time,
                            end_time=event.end_time,
                            access_before_schedule=event.access_before_schedule
                            if hasattr(event, "access_before_schedule")
                            else None,
                            timer=None,
                            timer_type=TimerType.NOT_SET,
                            one_time_completion=event.one_time_completion
                            if hasattr(event, "one_time_completion")
                            else None,
                            periodicity=event.periodicity.upper(),
                            start_date=event.start_date if hasattr(event, "start_date") else None,
                            end_date=event.end_date if hasattr(event, "end_date") else None,
                            selected_date=event.selected_date if hasattr(event, "selected_date") else None,
                            user_id=event.user_id,
                            activity_id=activity.id,
                            activity_flow_id=None,
                            event_type=EventType.ACTIVITY,
                        ),
                        include_history=True,
                    )
                    default_always_available_event_created = True
                except IntegrityError as e:
                    raise EventIdAlreadyExistsError(event.id, activity.id) from e
            else:
                # This should be a new event, so let's just create it
                created_event = await schedule_service.create_schedule(
                    EventRequest(
                        start_time=event.start_time,
                        end_time=event.end_time,
                        access_before_schedule=event.access_before_start_time
                        if hasattr(event, "access_before_start_time")
                        else None,
                        one_time_completion=event.one_time_completion
                        if hasattr(event, "one_time_completion")
                        else None,
                        respondent_id=event.user_id,
                        activity_id=activity.id,
                        flow_id=None,
                        periodicity=PeriodicityRequest(
                            type=event.periodicity.upper(),
                            start_date=event.start_date if hasattr(event, "start_date") else None,
                            end_date=event.end_date if hasattr(event, "end_date") else None,
                            selected_date=event.selected_date if hasattr(event, "selected_date") else None,
                        ),
                        notification=Notification(
                            notifications=[
                                NotificationSettingRequest(
                                    trigger_type=notification.trigger_type,
                                    from_time=notification.from_time if hasattr(notification, "from_time") else None,
                                    to_time=notification.to_time if hasattr(notification, "to_time") else None,
                                    at_time=notification.at_time if hasattr(notification, "at_time") else None,
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
                    await update_event_details(
                        session=session,
                        existing_event_id=created_event.id,
                        new_event_id=event.id,
                        new_event_version=event.version,
                        new_event_created_at=event.created_at,
                        include_history=True,
                    )
                except IntegrityError as e:
                    raise EventIdAlreadyExistsError(event.id, activity.id) from e


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
                        await applet_service.create(
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
                            applet=applet,
                        )
    except Exception as e:
        if not from_cli:
            raise e
        elif isinstance(e, SeedError):
            typer.echo(typer.style(f"ERROR: {str(e)}", fg=typer.colors.RED))
        else:
            traceback.print_exc()
