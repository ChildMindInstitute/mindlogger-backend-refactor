import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from apps.audit.crud import DEFAULT_PAGE_SIZE, AuditLogCRUD
from apps.audit.domain import AuditEvent


class AuditQueryService:
    def __init__(self, session: AsyncSession) -> None:
        self._crud = AuditLogCRUD(session)

    async def search_applet_events(
        self,
        applet_id: uuid.UUID,
        *,
        from_datetime: datetime.datetime | None = None,
        to_datetime: datetime.datetime | None = None,
        page: int = 1,
        limit: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[AuditEvent], int]:
        rows, total = await self._crud.search_applet_events(
            applet_id,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            page=page,
            limit=limit,
        )
        events = [AuditEvent.model_validate(row.payload) for row in rows]
        return events, total
