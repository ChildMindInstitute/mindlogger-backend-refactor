from fastapi.routing import APIRouter
from starlette import status

from apps.audit.api import applet_audit_export
from apps.audit.domain import AuditEvent
from apps.shared.domain import ResponseMulti
from apps.shared.domain.response import AUTHENTICATION_ERROR_RESPONSES, DEFAULT_OPENAPI_RESPONSE

router = APIRouter(prefix="/audit", tags=["Audit"])

router.get(
    "/applets/{applet_id}/events",
    status_code=status.HTTP_200_OK,
    response_model=ResponseMulti[AuditEvent],
    response_model_by_alias=True,
    responses={
        status.HTTP_200_OK: {"model": ResponseMulti[AuditEvent]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
    },
)(applet_audit_export)
