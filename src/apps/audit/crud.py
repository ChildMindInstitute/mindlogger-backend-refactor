import datetime
import uuid

from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert

from apps.audit.constants import ACCOUNT_LEVEL_EXPORT_ACTIONS
from apps.audit.db.schemas import AuditLogSchema
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from infrastructure.database.crud import BaseCRUD

DEFAULT_PAGE_SIZE = 1000


def _to_naive_utc(value: datetime.datetime) -> datetime.datetime:
    """Normalise a datetime to naive UTC to match the stored ``event_timestamp``."""
    if value.tzinfo is not None:
        value = value.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    return value


class AuditLogCRUD(BaseCRUD[AuditLogSchema]):
    schema_class = AuditLogSchema

    async def save(self, schema: AuditLogSchema) -> None:
        """Insert an audit log row.

        Uses ``ON CONFLICT (event_id) DO NOTHING`` so that a retried worker
        task (which re-delivers the same event) does not create a duplicate
        row — inserts are idempotent per ``event_id``.
        """
        query = (
            insert(AuditLogSchema)
            .values(
                event_id=schema.event_id,
                event_timestamp=schema.event_timestamp,
                event_action=schema.event_action,
                event_outcome=schema.event_outcome,
                user_id=schema.user_id,
                applet_ids=schema.applet_ids,
                payload=schema.payload,
            )
            .on_conflict_do_nothing(index_elements=[AuditLogSchema.event_id])
        )
        await self._execute(query)

    async def search_applet_events(
        self,
        applet_id: uuid.UUID,
        *,
        from_datetime: datetime.datetime | None = None,
        to_datetime: datetime.datetime | None = None,
        page: int = 1,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[AuditLogSchema], int]:
        """Events for an applet's audit export.

        Returns the applet's own events plus account-level events
        (``ACCOUNT_LEVEL_EXPORT_ACTIONS``) for its manager-class users. Membership
        is resolved at query time against current roles, so an account event stops
        appearing once the user loses their role on the applet, and events from
        before the user's access was granted are never surfaced.
        """
        # Users with a manager-class role on this applet. Their account-level events
        # (login/logout/MFA/...) are surfaced in the export even though those events
        # carry no applet id; respondents are intentionally excluded. Only events
        # from the access grant onwards qualify — adding a member must not expose
        # their earlier session history (both columns are naive UTC).
        privileged_access = (
            select(UserAppletAccessSchema.id)
            .where(
                UserAppletAccessSchema.applet_id == applet_id,
                UserAppletAccessSchema.role.in_(Role.managers()),
                UserAppletAccessSchema.soft_exists(),
                UserAppletAccessSchema.user_id == AuditLogSchema.user_id,
                UserAppletAccessSchema.created_at <= AuditLogSchema.event_timestamp,
            )
            .exists()
        )

        scope = or_(
            AuditLogSchema.applet_ids.contains([applet_id]),
            and_(
                AuditLogSchema.event_action.in_(ACCOUNT_LEVEL_EXPORT_ACTIONS),
                privileged_access,
            ),
        )

        conditions = [scope]
        if from_datetime is not None:
            conditions.append(AuditLogSchema.event_timestamp >= _to_naive_utc(from_datetime))
        if to_datetime is not None:
            conditions.append(AuditLogSchema.event_timestamp < _to_naive_utc(to_datetime))

        where = and_(*conditions)

        query = (
            select(AuditLogSchema)
            .where(where)
            .order_by(AuditLogSchema.event_timestamp.asc(), AuditLogSchema.event_id.asc())
            .limit(limit)
            .offset((page - 1) * limit)
        )
        rows = (await self._execute(query)).scalars().all()

        count_query = select(func.count()).select_from(AuditLogSchema).where(where)
        total = (await self._execute(count_query)).scalar() or 0

        return list(rows), total
