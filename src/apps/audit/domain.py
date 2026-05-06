from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import ConfigDict, Field, computed_field

from apps.shared.domain import PublicModel
from config import settings

from .enums import EventAction, EventKind, EventOutcome


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

    model_config = ConfigDict(serialize_by_alias=True)

    timestamp: Annotated[
        datetime,
        Field(alias="@timestamp", default_factory=lambda: datetime.now(timezone.utc)),
    ]
    error_type: Annotated[str | None, Field(alias="error.type")] = None  # if event_outcome="failure"
    event_action: Annotated[EventAction, Field(alias="event.action")]
    event_id: Annotated[UUID, Field(alias="event.id", default_factory=uuid4)]
    event_kind: Annotated[EventKind, Field(alias="event.kind")] = EventKind.EVENT
    event_outcome: Annotated[EventOutcome, Field(alias="event.outcome")] = EventOutcome.SUCCESS
    event_module: Annotated[str, Field(alias="event.module")] = "curious"
    event_dataset: Annotated[str, Field(alias="event.dataset")] = "curious.audit"
    service_name: Annotated[str, Field(alias="service.name", default=settings.service.name)]
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
    curious_applet_id: Annotated[list[UUID] | None, Field(alias="curious.applet_id")] = None
    curious_subject_id: Annotated[list[UUID] | None, Field(alias="curious.subject_id")] = None
    curious_flow_id: Annotated[list[UUID] | None, Field(alias="curious.flow_id")] = None
    curious_activity_id: Annotated[list[UUID] | None, Field(alias="curious.activity_id")] = None
    curious_submit_id: Annotated[list[UUID] | None, Field(alias="curious.submit_id")] = None
    curious_answer_id: Annotated[list[UUID] | None, Field(alias="curious.answer_id")] = None

    @computed_field(alias="_id")
    @property
    def id(self) -> UUID:
        """Reuse ECS event ID "event.id" as OpenSearch document ID "_id"."""
        return self.event_id
