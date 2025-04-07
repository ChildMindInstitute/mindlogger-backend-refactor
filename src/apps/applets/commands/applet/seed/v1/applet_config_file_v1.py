import uuid
from datetime import UTC, date, datetime, time
from typing import Annotated, Literal, Optional, Union, cast

from pydantic import AnyHttpUrl, BaseModel, Extra, Field, validator

from apps.applets.commands.applet.seed.errors import (
    AppletOwnerWithInvalidRolesError,
    AppletOwnerWithoutUserIdError,
    DuplicatAppletIdsError,
    DuplicateUserEmailsError,
    DuplicateUserIdsError,
    FullAccountWithoutRespondentRoleError,
    InvalidAppletError,
    InvalidFirstEventError,
    LimitedAccountWithRolesError,
    NonReviewerSubjectWithRevieweesError,
    SubjectUserNotPresentError,
)


class StrictBaseModel(BaseModel):
    class Config:
        extra = Extra.forbid


class UserConfig(StrictBaseModel):
    id: uuid.UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    first_name: str = Field(..., description="User first name")
    last_name: str = Field(..., description="User last name")
    password: str = Field(..., description="User password")
    created_at: datetime = Field(
        default=datetime.now(tz=UTC).replace(tzinfo=None), description="The date when the user was created"
    )

    @validator("created_at")
    def remove_timezone(cls, created_at: datetime):
        return created_at.replace(tzinfo=None)


class SubjectConfig(StrictBaseModel):
    id: uuid.UUID = Field(..., description="Subject ID")
    created_at: datetime = Field(
        default=datetime.now(tz=UTC).replace(tzinfo=None), description="Date when the subject was created"
    )
    user_id: Optional[uuid.UUID] = Field(None, description="User ID for full accounts and team members")
    email: Optional[str] = Field(None, description="Email address that received the applet invitation")
    secret_user_id: str = Field(..., description="Subject secret user ID. Should be unique within the applet")
    first_name: str = Field(..., min_length=1, description="Subject first name")
    last_name: str = Field(..., min_length=1, description="Subject last name")
    nickname: Optional[str] = Field(None, description="Optional subject nickname")
    roles: set[Literal["super_admin", "owner", "manager", "coordinator", "editor", "reviewer", "respondent"]] = Field(
        set(), description="Role of the subject in the applet"
    )
    reviewer_subjects: set[uuid.UUID] = Field(
        default=set(),
        description="List of UUIDs of subjects who this reviewer will review",
    )
    tag: Optional[Literal["Child", "Parent", "Teacher", "Team"]] = Field(default=None, description="Subject tag")

    @validator("created_at")
    def remove_timezone(cls, created_at: datetime):
        return created_at.replace(tzinfo=None)

    @validator("roles")
    def validate_respondent_role(cls, roles, values: dict):
        subject_id = cast(uuid.UUID, values.get("id"))
        if values.get("user_id") is not None and "respondent" not in roles:
            raise FullAccountWithoutRespondentRoleError(subject_id)

        if values.get("user_id") is None and len(roles) > 0:
            raise LimitedAccountWithRolesError(subject_id)

        if "owner" in roles:
            if len(roles) > 2:
                raise AppletOwnerWithInvalidRolesError(subject_id)
            elif values.get("user_id") is None:
                raise AppletOwnerWithoutUserIdError(subject_id)

        if values.get("reviewer_subjects") is not None and "reviewer" not in roles:
            raise NonReviewerSubjectWithRevieweesError(subject_id)

        return roles

    class Config:
        @staticmethod
        def schema_extra(schema: dict):
            roles_schema = schema.get("properties", {}).get("roles", {})
            roles_schema.update(
                {
                    "contains": {"const": "respondent"},
                    "minContains": 1,
                    "errorMessage": "Must contain the 'respondent' role",
                }
            )
            schema["properties"]["roles"] = roles_schema


class FixedNotificationConfig(StrictBaseModel):
    trigger_type: Literal["fixed"] = Field(..., description="Trigger type for fixed notifications")
    at_time: Optional[time] = Field(
        default=None,
        description="Time when the notification should be sent",
    )


class RandomNotificationConfig(StrictBaseModel):
    trigger_type: Literal["random"] = Field(
        ..., description="Trigger type for random notifications within a given time period"
    )
    from_time: Optional[time] = Field(..., description="Start time for random notifications")
    to_time: Optional[time] = Field(..., description="End time for random notifications")


NotificationConfig = Annotated[
    Union[FixedNotificationConfig, RandomNotificationConfig],
    Field(
        ...,
        discriminator="trigger_type",
    ),
]


class ReminderConfig(StrictBaseModel):
    activity_incomplete: int = Field(
        ...,
        description="Number of consecutive days that the user has not completed the activity after which to trigger the"
        " reminder",
    )
    reminder_time: time = Field(..., description="Time when the reminder should be sent")


class BaseEventConfig(StrictBaseModel):
    id: uuid.UUID = Field(..., description="Event ID")
    user_id: Optional[uuid.UUID] = Field(None, description="User ID for individual schedule events")
    is_deleted: bool = Field(default=False, description="Whether the event has been deleted. Default is False")
    version: str = Field(
        ..., description="Event version in the format YYYYMMdd-n (e.g. 20250301-1)", regex=r"^\d{8}-\d{1,4}$"
    )
    created_at: datetime = Field(..., description="Date when the event was created")
    notifications: list[NotificationConfig] = Field(
        default=[],
        description="List of notifications for the event. Each notification is a dictionary with keys: ",
    )
    reminder: Optional[ReminderConfig] = Field(default=None, description="Reminder settings for the event")

    @validator("created_at")
    def remove_timezone(cls, created_at: datetime):
        return created_at.replace(tzinfo=None)


class AlwaysAvailableEventConfig(BaseEventConfig):
    periodicity: Literal["ALWAYS"] = Field(
        ..., description="Event periodicity. Can be one of ALWAYS, ONCE, DAILY, WEEKLY, WEEKDAYS, MONTHLY"
    )
    start_time: time = Field(..., description="Event start time")
    end_time: time = Field(..., description="Event end time")
    one_time_completion: bool = Field(
        default=False,
        description="Whether the activity or flow can only be completed once per day. "
        "Applies only to always available periodicity",
    )


class OnceEventConfig(BaseEventConfig):
    periodicity: Literal["ONCE"] = Field(
        ..., description="Event periodicity. Can be one of ALWAYS, ONCE, DAILY, WEEKLY, WEEKDAYS, MONTHLY"
    )
    selected_date: date = Field(..., description="Selected date for the event")
    start_time: time = Field(..., description="Event start time")
    end_time: time = Field(..., description="Event end time")
    access_before_start_time: bool = Field(
        default=False, description="Whether to allow access before the event start time"
    )


class DailyEventConfig(BaseEventConfig):
    periodicity: Literal["DAILY"] = Field(
        ..., description="Event periodicity. Can be one of ALWAYS, ONCE, DAILY, WEEKLY, WEEKDAYS, MONTHLY"
    )
    start_date: date = Field(..., description="Event start date")
    end_date: date = Field(..., description="Event end date")
    start_time: time = Field(..., description="Event start time")
    end_time: time = Field(..., description="Event end time")
    access_before_start_time: bool = Field(
        default=False, description="Whether to allow access before the event start time"
    )


class WeeklyEventConfig(BaseEventConfig):
    periodicity: Literal["WEEKLY"] = Field(
        ..., description="Event periodicity. Can be one of ALWAYS, ONCE, DAILY, WEEKLY, WEEKDAYS, MONTHLY"
    )
    start_date: date = Field(..., description="Event start date")
    end_date: date = Field(..., description="Event end date")
    selected_date: date = Field(..., description="Selected date for the event recurrence")
    start_time: time = Field(..., description="Event start time")
    end_time: time = Field(..., description="Event end time")
    access_before_start_time: bool = Field(
        default=False, description="Whether to allow access before the event start time"
    )


class WeekdaysEventConfig(BaseEventConfig):
    periodicity: Literal["WEEKDAYS"] = Field(
        ..., description="Event periodicity. Can be one of ALWAYS, ONCE, DAILY, WEEKLY, WEEKDAYS, MONTHLY"
    )
    start_date: date = Field(..., description="Event start date")
    end_date: date = Field(..., description="Event end date")
    start_time: time = Field(..., description="Event start time")
    end_time: time = Field(..., description="Event end time")
    access_before_start_time: bool = Field(
        default=False, description="Whether to allow access before the event start time"
    )


class MonthlyEventConfig(BaseEventConfig):
    periodicity: Literal["MONTHLY"] = Field(
        ..., description="Event periodicity. Can be one of ALWAYS, ONCE, DAILY, WEEKLY, WEEKDAYS, MONTHLY"
    )
    start_date: date = Field(..., description="Event start date")
    end_date: date = Field(..., description="Event end date")
    selected_date: date = Field(..., description="Selected date for the event recurrence")
    start_time: time = Field(..., description="Event start time")
    end_time: time = Field(..., description="Event end time")
    access_before_start_time: bool = Field(
        default=False, description="Whether to allow access before the event start time"
    )


EventConfig = Annotated[
    Union[
        AlwaysAvailableEventConfig,
        OnceEventConfig,
        DailyEventConfig,
        WeeklyEventConfig,
        WeekdaysEventConfig,
        MonthlyEventConfig,
    ],
    Field(
        ...,
        discriminator="periodicity",
    ),
]


class AssignmentConfig(StrictBaseModel):
    id: uuid.UUID = Field(..., description="Assignment ID")
    assignment_type: Literal["activity", "flow"] = Field(..., description="Type of the assignment")
    activity_or_flow_id: uuid.UUID = Field(..., description="Activity or flow ID")
    respondent_subject_id: uuid.UUID = Field(
        ..., description="ID of the subject to whom the activity or flow is assigned"
    )
    target_subject_id: uuid.UUID = Field(
        ..., description="ID of the subject about whom the respondent will provide answers"
    )


class ReportServerConfig(StrictBaseModel):
    ip_address: AnyHttpUrl = Field(..., description="IP address of the report server")
    public_key: str = Field(..., min_length=1, description="RSA Public key for the report server")
    recipients: list[str] = Field(default=[], description="List of email addresses to receive reports")
    include_user_id: bool = Field(default=False, description="Whether to include user ID in the report")
    include_case_id: bool = Field(default=False)
    email_body: str = Field(..., min_length=1, description="Email body for the report")


class ActivityConfig(StrictBaseModel):
    id: uuid.UUID = Field(..., description="Activity ID")
    name: str = Field(..., description="Activity name")
    description: str = Field("", description="Activity description")
    is_hidden: bool = Field(False, description="Whether the activity is hidden")
    created_at: datetime = Field(
        datetime.now(tz=UTC).replace(tzinfo=None), description="Date when the activity was created"
    )
    auto_assign: bool = Field(True, description="Whether the activity is auto-assigned to all participants")
    events: list[EventConfig] = Field(..., min_items=1, description="List of scheduled events for this activity")

    @validator("created_at")
    def remove_timezone(cls, created_at: datetime):
        return created_at.replace(tzinfo=None)

    @validator("events")
    def validate_events(cls, events: list[EventConfig], values: dict):
        first_event = events[0]
        if first_event.periodicity != "ALWAYS":
            raise InvalidFirstEventError(first_event.id, "Periodicity must be set to ALWAYS")
        elif first_event.user_id is not None:
            raise InvalidFirstEventError(first_event.id, "Must be on the default schedule (user_id should be null)")

        return events


class FlowConfig(StrictBaseModel):
    id: uuid.UUID = Field(..., description="Flow ID")
    name: str = Field(..., description="Flow name")
    description: str = Field("", description="Flow description")
    is_hidden: bool = Field(False, description="Whether the flow is hidden")
    created_at: datetime = Field(
        datetime.now(tz=UTC).replace(tzinfo=None), description="Date when the flow was created"
    )
    auto_assign: bool = Field(True, description="Whether the flow is auto-assigned to all participants")
    events: list[EventConfig] = Field(..., min_items=1, description="List of scheduled events for this flow")
    assignments: list[AssignmentConfig] = Field(default=[], description="List of flow assignments")
    activities: list[uuid.UUID] = Field(
        ..., min_items=1, description="List of activity IDs in the flow, arranged in the desired order"
    )

    @validator("created_at")
    def remove_timezone(cls, created_at: datetime):
        return created_at.replace(tzinfo=None)


class AppletEncryptionConfig(StrictBaseModel):
    public_key: str = Field(..., description="Public key for encryption")
    prime: str = Field(..., description="Large prime number array")
    base: str = Field(..., description="Generator base")
    account_id: uuid.UUID = Field(..., description="Applet owner user ID")


class AppletConfig(StrictBaseModel):
    id: uuid.UUID = Field(..., description="Applet ID")
    encryption: AppletEncryptionConfig = Field(
        ..., description="Encryption config for an existing applet from the applet owner"
    )
    display_name: str = Field(..., description="Applet display name")
    description: str = Field("", description="Applet description")
    created_at: datetime = Field(
        datetime.now(tz=UTC).replace(tzinfo=None), description="Date when the applet was created"
    )
    subjects: list[SubjectConfig] = Field(
        ..., min_items=1, description="List of subjects in the applet. You must provide at least the applet owner"
    )
    activities: list[ActivityConfig] = Field(..., min_items=1, description="List of activities in the applet")
    report_server: Optional[ReportServerConfig] = Field(
        default=None, description="Report server settings for the applet"
    )

    @validator("created_at")
    def remove_timezone(cls, created_at: datetime):
        return created_at.replace(tzinfo=None)

    @validator("activities")
    def validate_activities(cls, activities: list[ActivityConfig], values: dict):
        activity_id_counts: dict[uuid.UUID, int] = {}
        duplicate_activity_ids: set[uuid.UUID] = set()
        applet_id = cast(uuid.UUID, values.get("id"))

        if len(activities) == 0:
            # We'll need to update this validation when we start supporting flows
            raise InvalidAppletError(applet_id, "The applet must contain at least one activity")

        for activity in activities:
            activity_id_counts[activity.id] = activity_id_counts.get(activity.id, 0) + 1
            if activity_id_counts[activity.id] > 1:
                duplicate_activity_ids.add(activity.id)

        # Ensure all activity IDs are unique
        if len(duplicate_activity_ids) > 0:
            raise InvalidAppletError(
                applet_id, f"The activity IDs are repeated: {', '.join(map(str, duplicate_activity_ids))}"
            )

        event_id_version_counts: dict[str, int] = {}
        duplicate_event_id_versions: set[str] = set()

        for activity in activities:
            for event in activity.events:
                id_version = f"{event.id}_{event.version}"
                event_id_version_counts[id_version] = event_id_version_counts.get(id_version, 0) + 1
                if event_id_version_counts[id_version] > 1:
                    duplicate_event_id_versions.add(f"{event.id}, {event.version}")

        # Ensure all event IDs and versions are unique
        if len(duplicate_event_id_versions) > 0:
            raise InvalidAppletError(
                applet_id=applet_id,
                message=f"Contains multiple events with the same ID and version: "
                f"{', '.join(duplicate_event_id_versions)}",
            )

        return activities

    @validator("subjects")
    def validate_subjects(cls, subjects: list[SubjectConfig], values: dict):
        subject_id_counts: dict[uuid.UUID, int] = {}
        secret_user_id_counts: dict[str, int] = {}
        duplicate_subject_ids: set[uuid.UUID] = set()
        duplicate_secret_user_ids: set[str] = set()
        owner_subject_ids: set[uuid.UUID] = set()
        applet_id = cast(uuid.UUID, values.get("id"))

        for subject in subjects:
            subject_id_counts[subject.id] = subject_id_counts.get(subject.id, 0) + 1
            secret_user_id_counts[subject.secret_user_id] = secret_user_id_counts.get(subject.secret_user_id, 0) + 1
            if subject_id_counts[subject.id] > 1:
                duplicate_subject_ids.add(subject.id)
            if secret_user_id_counts[subject.secret_user_id] > 1:
                duplicate_secret_user_ids.add(subject.secret_user_id)
            if "owner" in subject.roles:
                owner_subject_ids.add(subject.id)

        # Ensure all subject IDs are unique
        if len(duplicate_subject_ids) > 0:
            raise InvalidAppletError(
                applet_id, f"The subject IDs are repeated: {', '.join(map(str, duplicate_subject_ids))}"
            )

        # Ensure all secret user IDs are unique
        if len(duplicate_secret_user_ids) > 0:
            raise InvalidAppletError(
                applet_id, f"The secret user IDs are repeated: {', '.join(duplicate_secret_user_ids)}"
            )

        if len(owner_subject_ids) != 1:
            raise InvalidAppletError(applet_id, f"Must have exactly one owner, found {len(owner_subject_ids)} owners")

        applet_owner_id = owner_subject_ids.pop()
        owner_subject = next(subject for subject in subjects if subject.id == applet_owner_id)

        if not owner_subject.user_id:
            raise AppletOwnerWithoutUserIdError(owner_subject.id)

        return subjects


class AppletConfigFileV1(StrictBaseModel):
    version: Literal["1.0"] = Field(..., description="Version of the config file")

    users: list[UserConfig] = Field(default=[], description="List of users to create")
    applets: list[AppletConfig] = Field(default=[], description="List of applets to create")

    @validator("users")
    def validate_user_ids(cls, users: list[UserConfig]):
        user_id_counts: dict[uuid.UUID, int] = {}
        user_email_counts: dict[str, int] = {}
        duplicate_user_ids: set[uuid.UUID] = set()
        duplicate_user_emails: set[str] = set()

        for user in users:
            user_id_counts[user.id] = user_id_counts.get(user.id, 0) + 1
            user_email_counts[user.email] = user_email_counts.get(user.email, 0) + 1
            if user_id_counts[user.id] > 1:
                duplicate_user_ids.add(user.id)
            if user_email_counts[user.email] > 1:
                duplicate_user_emails.add(user.email)

        # Ensure all user IDs are unique
        if len(duplicate_user_ids) > 0:
            raise DuplicateUserIdsError(duplicate_user_ids)

        # Ensure all user emails are unique
        if len(duplicate_user_emails) > 0:
            raise DuplicateUserEmailsError(duplicate_user_emails)

        return users

    @validator("applets")
    def validate_applet_ids(cls, applets: list[AppletConfig], values: dict):
        applet_id_counts: dict[uuid.UUID, int] = {}
        duplicate_applet_ids: set[uuid.UUID] = set()

        # Ensure all full account applet subjects are in the users list
        user_ids: set[uuid.UUID] = {user.id for user in values.get("users", [])}
        for applet in applets:
            applet_id_counts[applet.id] = applet_id_counts.get(applet.id, 0) + 1
            if applet_id_counts[applet.id] > 1:
                duplicate_applet_ids.add(applet.id)
            for subject in applet.subjects:
                if subject.user_id and subject.user_id not in user_ids:
                    raise SubjectUserNotPresentError(
                        subject_id=subject.id,
                        user_id=subject.user_id,
                        applet_id=applet.id,
                    )

        # Ensure all applet IDs are unique
        if len(duplicate_applet_ids) > 0:
            raise DuplicatAppletIdsError(duplicate_applet_ids)

        return applets
