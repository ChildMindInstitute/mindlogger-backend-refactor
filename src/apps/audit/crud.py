import datetime
import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert

from apps.audit.db.schemas import AuditLogSchema
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
        row — preserving the idempotency OpenSearch gave us via ``id=event.id``.
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
        conditions = [AuditLogSchema.applet_ids.any(applet_id)]
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
