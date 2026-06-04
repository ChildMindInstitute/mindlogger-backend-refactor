from enum import StrEnum
from functools import cached_property


class EventAction(StrEnum):
    """event.action values defined for Curious

    Uses colon-separated format "{resource}:{subject}:{action}":
    - "{resource}" all lowercase or underscore
    - "{subject}" all lowercase or underscore or colon or omitted
    - "{action}" all lowercase or underscore

    Note that "{subject}" can contain colons or be omitted.

    If omitted, "{subject}" is implied to be the same as "{resource}".
    """

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
    APPLET_ACCESS_GRANT = "applet:access:grant"
    APPLET_ACCESS_REVOKE = "applet:access:revoke"
    APPLET_RETENTION_UPDATE = "applet:retention:update"
    APPLET_REPORT_UPDATE = "applet:report:update"

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

    # Applet audit
    APPLET_AUDIT_EXPORT = "applet:audit:export"

    @cached_property
    def _parts(self) -> tuple[str, ...]:
        """Split into parts by colon ":"

        - ("a", "b", "c", "d") for event "a:b:c:d"
        - ("foo", "bar", "baz") for event "foo:bar:baz"
        - ("toto", "tata") for event "toto:tata"
        """
        return tuple(self.value.split(":"))

    @cached_property
    def resource(self) -> str:
        """First part of enum value

        - "a" for event "a:b:c:d"
        - "foo" for event "foo:bar:baz"
        - "toto" for event "toto:tata"
        """
        return self._parts[0]

    @cached_property
    def subject(self) -> str:
        """Middle part of enum value, or resource if middle part does not exist

        - "b:c" for event "a:b:c:d"
        - "bar" for event "foo:bar:baz"
        - "toto" for event "toto:tata"
        """
        return ":".join(self._parts[1:-1]) or self.resource

    @cached_property
    def action(self) -> str:
        """Last part of enum value

        - "d" for event "a:b:c:d"
        - "baz" for event "foo:bar:baz"
        - "tata" for event "toto:tata"
        """
        return self._parts[-1]


class EventKind(StrEnum):
    """event.kind values defined by ECS"""

    # https://www.elastic.co/docs/reference/ecs/ecs-allowed-values-event-kind
    EVENT = "event"


class EventCategory(StrEnum):
    """event.category values defined by ECS"""

    # https://www.elastic.co/docs/reference/ecs/ecs-allowed-values-event-category
    AUTHENTICATION = "authentication"
    SESSION = "session"
    DATABASE = "database"
    FILE = "file"
    IAM = "iam"
    CONFIGURATION = "configuration"
    WEB = "web"


class EventType(StrEnum):
    """event.type values defined by ECS"""

    # https://www.elastic.co/docs/reference/ecs/ecs-allowed-values-event-type
    START = "start"
    END = "end"
    INFO = "info"
    ACCESS = "access"
    CHANGE = "change"
    CREATION = "creation"
    DELETION = "deletion"
    DENIED = "denied"


class EventOutcome(StrEnum):
    """event.outcome values defined by ECS"""

    # https://www.elastic.co/docs/reference/ecs/ecs-allowed-values-event-outcome
    SUCCESS = "success"
    FAILURE = "failure"
    UNKNOWN = "unknown"
