import datetime
import uuid

from pydantic import Field, root_validator, validator
from sqlalchemy import Unicode
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg
from sqlalchemy_utils import StringEncryptedType

from apps.applets.domain.base import Encryption
from apps.shared.domain import InternalModel, PublicModel
from apps.shared.encryption import get_key
from apps.workspaces.constants import StorageType
from apps.workspaces.domain.constants import Role
from apps.workspaces.errors import InvalidAppletIDFilter

__all__ = [
    "PublicWorkspace",
    "UserWorkspace",
    "WorkspaceRespondent",
    "PublicWorkspaceRespondent",
    "WorkspaceManager",
    "PublicWorkspaceManager",
    "WorkspaceInfo",
    "PublicWorkspaceInfo",
    "WorkspaceArbitrary",
    "WorkspaceArbitraryCreate",
    "WorkspaceArbitraryFields",
]


class PublicWorkspace(PublicModel):
    """This model is returned to the user their current workspace."""

    owner_id: uuid.UUID = Field(
        description="This field represents the applet owner id",
    )
    workspace_name: str = Field(
        description="This field represents the name of workspace "
        "which is consists of 'first name', 'last name' of user "
        "which is applet owner and prefix",
    )


class UserWorkspace(InternalModel):
    """This model used for internal needs, returned to the user
    their current workspace.
    """

    user_id: uuid.UUID = Field(
        description="This field represents the applet owner id",
    )
    workspace_name: str = Field(
        description="This field represents the name of workspace "
        "which is consists of 'first name', 'last name' of user "
        "which is applet owner and prefix",
    )


class WorkspaceAppletEncryption(InternalModel):
    public_key: str
    prime: str
    base: str
    account_id: str


class WorkspaceRespondentDetails(InternalModel):
    applet_id: uuid.UUID
    applet_display_name: str
    applet_image: str | None
    access_id: str | None = None
    respondent_nickname: str | None = None
    respondent_secret_id: str | None = None
    has_individual_schedule: bool = False
    encryption: WorkspaceAppletEncryption | None = None
    subject_id: uuid.UUID

    @root_validator
    def decrypt_nickname(cls, values):
        nickname = values.get("respondent_nickname")
        if nickname:
            nickname = StringEncryptedType(Unicode, get_key).process_result_value(
                nickname, dialect=PGDialect_asyncpg.name
            )
            values["respondent_nickname"] = str(nickname)

        return values


class WorkspaceRespondent(InternalModel):
    id: uuid.UUID | None
    nicknames: list[str] | None = None
    secret_ids: list[str] | None = None
    is_anonymous_respondent: bool
    last_seen: datetime.datetime | None
    is_pinned: bool = False
    details: list[WorkspaceRespondentDetails] | None = None
    user_id: uuid.UUID | None
    status: str
    email: str | None
    subjects: list[uuid.UUID]


class AppletRole(InternalModel):
    access_id: uuid.UUID
    role: Role
    reviewer_subjects: list[str] | None = None


class WorkspaceManagerApplet(InternalModel):
    id: uuid.UUID
    display_name: str
    image: str | None
    roles: list[AppletRole]
    encryption: WorkspaceAppletEncryption


class WorkspaceManager(InternalModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email_encrypted: str | None
    roles: list[Role]
    last_seen: datetime.datetime
    is_pinned: bool = False
    applets: list[WorkspaceManagerApplet] | None = None

    @validator("applets", pre=True)
    def group_applets(cls, value):
        applets = {}
        for applet_role in value:
            applet_id = applet_role["applet_id"]
            applet = applets.get(applet_id)
            if not applet:
                applet = {
                    "id": applet_id,
                    "display_name": applet_role["applet_display_name"],
                    "image": applet_role["applet_image"],
                    "roles": [],
                    "encryption": applet_role["encryption"],
                }

            subjects = []
            if applet_role["role"] == Role.REVIEWER:
                subjects = applet_role["reviewer_subjects"]

            applet["roles"].append(
                dict(
                    access_id=applet_role["access_id"],
                    role=applet_role["role"],
                    reviewer_subjects=subjects,
                )
            )
            applets[applet_id] = applet

        return list(applets.values())


class PublicWorkspaceRespondentDetails(PublicModel):
    applet_id: uuid.UUID
    applet_display_name: str
    applet_image: str | None
    access_id: uuid.UUID | None
    respondent_nickname: str | None = None
    respondent_secret_id: str | None = None
    has_individual_schedule: bool = False
    encryption: WorkspaceAppletEncryption | None = None
    subject_id: uuid.UUID


class PublicWorkspaceRespondent(PublicModel):
    id: uuid.UUID | None
    nicknames: list[str] | None
    secret_ids: list[str] | None
    is_anonymous_respondent: bool
    last_seen: datetime.datetime | None
    is_pinned: bool = False
    details: list[PublicWorkspaceRespondentDetails] | None = None
    status: str
    email: str | None
    subjects: list[uuid.UUID]


class PublicWorkspaceManager(PublicModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    email: str | None
    roles: list[Role]
    last_seen: datetime.datetime
    is_pinned: bool = False
    applets: list[WorkspaceManagerApplet] | None = None


class WorkspaceInfo(InternalModel):
    name: str
    has_managers: bool


class PublicWorkspaceInfo(PublicModel):
    name: str
    has_managers: bool


class WorkspaceApplet(InternalModel):
    id: uuid.UUID
    display_name: str
    image: str | None
    is_pinned: bool
    encryption: Encryption | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    version: str | None
    role: Role | None = Role.RESPONDENT
    type: str
    folders_applet_count: int
    description: dict | None
    activity_count: int | None


class WorkspaceSearchApplet(InternalModel):
    id: uuid.UUID
    display_name: str
    image: str | None
    is_pinned: bool
    encryption: Encryption | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    version: str | None
    role: Role | None = Role.RESPONDENT
    type: str
    folder_id: uuid.UUID | None
    folder_name: str | None


class WorkspaceAppletPublic(PublicModel):
    id: uuid.UUID
    display_name: str
    image: str | None
    is_pinned: bool
    encryption: Encryption | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    version: str | None
    role: Role | None
    type: str
    folders_applet_count: int
    description: dict | None
    activity_count: int | None


class WorkspaceSearchAppletPublic(PublicModel):
    id: uuid.UUID
    display_name: str
    image: str | None
    is_pinned: bool
    encryption: Encryption | None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    version: str | None
    role: Role | None = Role.RESPONDENT
    type: str
    folder_id: uuid.UUID | None
    folder_name: str | None


class WorkspacePrioritizedRole(PublicModel):
    role: Role | None


class AppletRoles(InternalModel):
    applet_id: uuid.UUID
    roles: list[Role]


class WorkspaceArbitraryFields(InternalModel):
    database_uri: str | None = None
    storage_type: str | None = None
    storage_url: str | None = None
    storage_access_key: str | None = None
    storage_secret_key: str | None = None
    storage_region: str | None = None
    storage_bucket: str | None = None
    use_arbitrary: bool

    def is_arbitrary_empty(self):
        return not any(
            [
                self.database_uri,
                self.storage_access_key,
                self.storage_secret_key,
                self.storage_region,
                self.storage_type,
                self.storage_url,
                self.storage_bucket,
                self.use_arbitrary,
            ]
        )

    @validator("use_arbitrary", always=True, pre=True)
    def to_bool(cls, value):
        if value is None:
            return False

        return value


class WorkSpaceArbitraryConsoleOutput(WorkspaceArbitraryFields):
    user_id: uuid.UUID
    email: str
    alembic_version: str | None

    @validator("use_arbitrary")
    def format_arbitrary_usage(cls, value):
        if value:
            return "[green]True[/green]"
        return "[red]False[/red]"


class WorkspaceArbitraryCreate(WorkspaceArbitraryFields):
    database_uri: str
    storage_secret_key: str
    storage_type: StorageType

    @root_validator()
    def validate_storage_settings(cls, values):
        storage_type = values["storage_type"]
        required = []
        if storage_type == StorageType.AWS:
            required = ["storage_access_key", "storage_region", "storage_bucket"]
        elif storage_type == StorageType.GCP:
            required = ["storage_url", "storage_bucket", "storage_access_key"]

        if required and not all((values[itm] is not None) for itm in required):
            raise ValueError(f"{', '.join(required)} are required " f"for {storage_type} storage")

        return values

    @validator("database_uri")
    def validate_database_uri(cls, value: str) -> str:
        driver_path = "postgresql+asyncpg://"
        if not value.startswith(driver_path):
            raise ValueError(f"Database uri must start with {driver_path}")
        return value


class WorkspaceArbitrary(WorkspaceArbitraryFields):
    id: uuid.UUID
    database_uri: str
    storage_secret_key: str
    storage_type: str
    user_id: uuid.UUID


class AnswerDbApplet(InternalModel):
    applet_id: uuid.UUID
    encryption: Encryption


class UserAnswersDBInfo(AnswerDbApplet):
    use_arbitrary: bool | None
    database_uri: str | None


class AnswerDbApplets(InternalModel):
    database_uri: str | None
    applets: list[AnswerDbApplet] = Field(default_factory=list)


class AppletIdsQuery(InternalModel):
    applet_ids: str | None = Field(None, alias="appletIDs")

    @validator("applet_ids")
    def convert_str_to_uuid(cls, value) -> list[uuid.UUID]:
        if not value:
            return []
        try:
            applet_ids = list(map(uuid.UUID, filter(None, value.split(","))))
        except ValueError:
            raise InvalidAppletIDFilter
        return applet_ids
