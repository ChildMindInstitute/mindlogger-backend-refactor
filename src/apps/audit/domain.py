from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import Field

from apps.shared.domain import PublicModel
from config import settings


class EventAction(StrEnum):
    """event.action values defined for Curious"""

    # User auth
    USER_SESSION_LOGIN = "user:session:login"
    USER_SESSION_LOGOUT = "user:session:logout"
    USER_SESSION_REFRESH = "user:session:refresh"
    USER_SESSION_INVALID = "user:session:invalid"

    # User IAM
    USER_CREATE = "user:create"
    USER_DELETE = "user:delete"
    USER_PASSWORD_CHANGE = "user:password:change"
    USER_PASSWORD_RECOVERY_INITIATE = "user:password:recovery:initiate"
    USER_PASSWORD_RECOVERY_APPROVE = "user:password:recovery:approve"
    USER_MFA_ENABLE = "user:mfa:enable"
    USER_MFA_DISABLE = "user:mfa:disable"
    USER_MFA_RECOVERY_VIEW = "user:mfa:recovery:view"
    USER_MFA_RECOVERY_DOWNLOAD = "user:mfa:recovery:download"
    USER_MFA_RECOVERY_USE = "user:mfa:recovery:use"

    # Workspace IAM
    WORKSPACE_ACCESS_GRANT = "workspace:access:grant"
    WORKSPACE_ACCESS_REVOKE = "workspace:access:revoke"

    # Applet IAM
    APPLET_CREATE = "applet:create"
    APPLET_DELETE = "applet:delete"
    APPLET_ENCRYPTION_UPDATE = "applet:encryption:update"
    APPLET_TRANSFER_INITIATE = "applet:transfer:initiate"
    APPLET_TRANSFER_ACCEPT = "applet:transfer:accept"
    APPLET_TRANSFER_DECLINE = "applet:transfer:decline"
    APPLET_INVITE_INITIATE = "applet:invite:initiate"
    APPLET_INVITE_ACCEPT = "applet:invite:accept"
    APPLET_INVITE_DECLINE = "applet:invite:decline"

    # Applet data access
    APPLET_SUBJECT_VIEW = "applet:subject:view"
    APPLET_ANSWER_VIEW = "applet:answer:view"
    APPLET_ANSWER_IDENTIFIER_VIEW = "applet:answer:identifier:view"
    APPLET_ANSWER_ASSESSMENT_VIEW = "applet:answer:assessment:view"
    APPLET_ANSWER_NOTE_VIEW = "applet:answer:note:view"
    APPLET_ANSWER_EXPORT = "applet:answer:export"

    # Applet file download
    APPLET_ANSWER_EHR_DOWNLOAD = "applet:answer:ehr:download"
    APPLET_ANSWER_FILE_DOWNLOAD = "applet:answer:file:download"
    APPLET_ANSWER_REPORT_DOWNLOAD = "applet:answer:report:download"


class EventOutcome(StrEnum):
    """event.outcome values defined by ECS"""

    SUCCESS = "success"
    FAILURE = "failure"
    UNKNOWN = "unknown"


class EventCategory(StrEnum):
    """event.category values defined by ECS"""

    AUTHENTICATION = "authentication"
    SESSION = "session"
    DATABASE = "database"
    FILE = "file"
    IAM = "iam"
    CONFIGURATION = "configuration"
    WEB = "web"


class EventType(StrEnum):
    """event.type values defined by ECS"""

    START = "start"
    END = "end"
    INFO = "info"
    ACCESS = "access"
    CHANGE = "change"
    CREATION = "creation"
    DELETION = "deletion"
    DENIED = "denied"


class AuditEvent(PublicModel):
    """Audit event

    Required for all events:
    - user_id
    - event_action

    Automatically populated fields:
    - timestamp
    - event_id
    - event_kind
    - event_module
    - event_dataset
    - service_name
    - service_environment

    Applicable to IAM events:
    - user_roles
    - user_target_id
    - user_target_email
    - user_target_roles

    Applicable to failures:
    - event_outcome
    - error_type

    Applicable to HTTP requests:
    - client_ip
    - http_request_id
    - http_request_method,
    - http_response_status_code
    - url_path
    - url_query

    Applicable to HTTP requests if Datadog is enabled:
    - trace_id

    Applicable to file downloads:
    - file_path

    Applicable to Curious database records:
    - curious_applet_id
    - curious_subject_id
    - curious_flow_id
    - curious_activity_id
    - curious_submit_id
    - curious_answer_id

    Notes:
    - Set user_id=None if there is no authenticated user.
    - Set event_outcome="failure" for failures.

    """

    timestamp: Annotated[
        datetime,
        Field(alias="@timestamp", default_factory=lambda: datetime.now(timezone.utc)),
    ]
    error_type: Annotated[str | None, Field(alias="error.type")] = None  # if event_outcome="failure"
    event_action: Annotated[EventAction, Field(alias="event.action")]
    event_outcome: Annotated[EventOutcome, Field(alias="event.outcome")] = EventOutcome.SUCCESS
    event_id: Annotated[UUID, Field(alias="event.id", default_factory=uuid4)]
    event_kind: Annotated[Literal["event"], Field(alias="event.kind")] = "event"
    event_module: Annotated[str, Field(alias="event.module")] = "curious"
    event_dataset: Annotated[str, Field(alias="event.dataset")] = "curious.audit"
    service_name: Annotated[str, Field(alias="service.name")] = "mindlogger-backend"
    service_environment: Annotated[str, Field(alias="service.environment", default=settings.env)]

    # User performing the action
    user_id: Annotated[UUID | None, Field(alias="user.id")]
    user_roles: Annotated[list[str] | None, Field(alias="user.roles")] = None

    # User being acted upon (if applicable)
    user_target_id: Annotated[UUID | None, Field(alias="user.target.id")] = None  # prefer ID if available
    user_target_email: Annotated[str | None, Field(alias="user.target.email")] = None  # email only if ID unavailable
    user_target_roles: Annotated[list[str] | None, Field(alias="user.target.roles")] = None

    # For HTTP requests
    client_ip: Annotated[str | None, Field(alias="client.ip")] = None
    http_request_id: Annotated[str | None, Field(alias="http.request.id")] = None  # from asgi-correlation-id
    http_request_method: Annotated[str | None, Field(alias="http.request.method")] = None
    http_response_status_code: Annotated[int | None, Field(alias="http.response.status_code")] = None
    trace_id: Annotated[str | None, Field(alias="trace.id")] = None  # from Datadog if enabled
    url_path: Annotated[str | None, Field(alias="url.path")] = None
    url_query: Annotated[str | None, Field(alias="url.query")] = None
    user_agent: Annotated[str | None, Field(alias="user_agent.original")] = None

    # For file downloads
    file_path: Annotated[str | None, Field(alias="file.path")] = None  # file download path

    # For Curious database records
    curious_applet_id: Annotated[UUID | list[UUID] | None, Field(alias="curious.applet_id")] = None
    curious_subject_id: Annotated[UUID | list[UUID] | None, Field(alias="curious.subject_id")] = None
    curious_flow_id: Annotated[UUID | list[UUID] | None, Field(alias="curious.flow_id")] = None
    curious_activity_id: Annotated[UUID | list[UUID] | None, Field(alias="curious.activity_id")] = None
    curious_submit_id: Annotated[UUID | list[UUID] | None, Field(alias="curious.submit_id")] = None
    curious_answer_id: Annotated[UUID | list[UUID] | None, Field(alias="curious.answer_id")] = None
