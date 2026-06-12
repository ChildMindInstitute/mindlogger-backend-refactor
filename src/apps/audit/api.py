import uuid
from datetime import timezone

from fastapi import Depends, Request

from apps.applets.service import AppletService
from apps.audit import http_audit_fields, log
from apps.audit.domain import AuditEvent
from apps.audit.enums import EventAction
from apps.audit.errors import InvalidAuditDateRangeError
from apps.audit.filters import AuditExportFilters
from apps.audit.query_service import AuditQueryService
from apps.authentication.deps import get_current_user
from apps.shared.domain import ResponseMulti
from apps.shared.exception import BaseError
from apps.shared.query_params import QueryParams, parse_query_params
from apps.users.domain import User
from apps.workspaces.service.check_access import CheckAccessService
from infrastructure.database.deps import get_session


async def applet_audit_export(
    applet_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    query_params: QueryParams = Depends(parse_query_params(AuditExportFilters)),
    session=Depends(get_session),
) -> ResponseMulti[AuditEvent]:
    try:
        await AppletService(session, user.id).exist_by_id(applet_id)
        await CheckAccessService(session, user.id).check_audit_export_access(applet_id)

        from_datetime = query_params.filters.get("from_datetime")
        to_datetime = query_params.filters.get("to_datetime")

        if from_datetime and from_datetime.tzinfo is None:
            from_datetime = from_datetime.replace(tzinfo=timezone.utc)
        if to_datetime and to_datetime.tzinfo is None:
            to_datetime = to_datetime.replace(tzinfo=timezone.utc)

        if from_datetime and to_datetime and from_datetime > to_datetime:
            raise InvalidAuditDateRangeError(path=["fromDatetime"])

        events, total = await AuditQueryService().search_applet_events(
            applet_id,
            from_datetime=from_datetime,
            to_datetime=to_datetime,
            page=query_params.page,
            limit=query_params.limit,
        )

        await log(
            AuditEvent(
                event_action=EventAction.APPLET_AUDIT_EXPORT,
                user_id=user.id,
                curious_applet_id=[applet_id],
                **http_audit_fields(request),
            )
        )

        return ResponseMulti(result=events, count=total)
    except BaseError as e:
        await log(
            AuditEvent(
                event_action=EventAction.APPLET_AUDIT_EXPORT,
                user_id=user.id,
                curious_applet_id=[applet_id],
                **http_audit_fields(request, e),
            )
        )
        raise
