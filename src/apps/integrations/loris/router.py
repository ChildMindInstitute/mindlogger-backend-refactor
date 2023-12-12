from fastapi.routing import APIRouter
from starlette import status

from apps.integrations.loris.api import start_transmit_process
from apps.integrations.loris.api.consent import (
    consent_create,
    consent_get_by_id,
    consent_get_by_user_id,
    consent_update,
)
from apps.integrations.loris.domain import PublicConsent
from apps.shared.domain import Response
from apps.shared.domain.response import (
    AUTHENTICATION_ERROR_RESPONSES,
    DEFAULT_OPENAPI_RESPONSE,
    NO_CONTENT_ERROR_RESPONSES,
)

router = APIRouter(prefix="/integrations/loris", tags=["Loris"])


router.post(
    "/publish",
    description="This endpoint is used to start transmit process from\
          ML to LORIS",
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        **DEFAULT_OPENAPI_RESPONSE,
        **AUTHENTICATION_ERROR_RESPONSES,
    },
)(start_transmit_process)


router.post(
    "/consent",
    response_model=Response[PublicConsent],
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_201_CREATED: {"model": Response[PublicConsent]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(consent_create)


router.get(
    "/consent/{consent_id}/",
    response_model=Response[PublicConsent],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicConsent]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(consent_get_by_id)


router.get(
    "/consent/users/{user_id}/",
    response_model=Response[PublicConsent],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicConsent]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(consent_get_by_user_id)


router.put(
    "/consent/{consent_id}/",
    response_model=Response[PublicConsent],
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {"model": Response[PublicConsent]},
        **AUTHENTICATION_ERROR_RESPONSES,
        **DEFAULT_OPENAPI_RESPONSE,
        **NO_CONTENT_ERROR_RESPONSES,
    },
)(consent_update)
