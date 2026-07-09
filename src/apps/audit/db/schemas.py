from sqlalchemy import Column, DateTime, Index, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

from infrastructure.database.base import Base


class AuditLogSchema(Base):
    """Audit event stored in Postgres.

    Append-only. A few columns are denormalized from the ECS document for
    filtering/sorting; the full event is kept in ``payload`` as the same
    dotted-alias JSON that is produced by ``AuditEvent.model_dump(mode="json")``.

    Note: for failed logins the denormalized ``user_id`` is resolved from the
    attempted email at persist time and may therefore be set even though
    ``payload["user.id"]`` stays ``null`` (see ``tasks._resolve_actor_from_email``).
    """

    __tablename__ = "audit_logs"

    event_id = Column(UUID(as_uuid=True), nullable=False, unique=True)
    event_timestamp = Column(DateTime(), nullable=False)
    event_action = Column(String(), nullable=False)
    event_outcome = Column(String(), nullable=True)
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    applet_ids = Column(ARRAY(UUID(as_uuid=True)), nullable=True)
    payload = Column(JSONB(), nullable=False)

    __table_args__ = (
        # Covers the date-range filter and the (timestamp, event_id) sort order.
        Index("ix_audit_logs_event_timestamp_event_id", "event_timestamp", "event_id"),
        # Covers `applet_ids @> ARRAY[:applet_id]` membership lookups.
        Index("ix_audit_logs_applet_ids", "applet_ids", postgresql_using="gin"),
    )
