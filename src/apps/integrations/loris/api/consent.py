import uuid

from fastapi import Body, Depends

from apps.authentication.deps import get_current_user
from apps.integrations.loris.domain.domain import ConsentRequest, ConsentUpdateRequest, PublicConsent
from apps.integrations.loris.service import ConsentService
from apps.shared.domain import Response
from apps.users.domain import User
from infrastructure.database import atomic
from infrastructure.database.deps import get_session


async def consent_create(
    schema: ConsentRequest = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[PublicConsent]:
    """Create a new consent."""
    async with atomic(session):
        service = ConsentService(session)
        consent = await service.create_consent(schema)

    return Response(result=PublicConsent(**consent.dict()))


async def consent_get_by_id(
    consent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[PublicConsent]:
    """Get a consent by id."""
    async with atomic(session):
        consent = await ConsentService(session).get_consent_by_id(consent_id=consent_id)
    return Response(result=PublicConsent(**consent.dict()))


async def consent_get_by_user_id(
    user_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[PublicConsent]:
    """Get a consent by user id."""
    async with atomic(session):
        consent = await ConsentService(session).get_consent_by_user_id(user_id=user_id)
    return Response(result=PublicConsent(**consent.dict()))


async def consent_update(
    consent_id: uuid.UUID,
    user: User = Depends(get_current_user),
    schema: ConsentUpdateRequest = Body(...),
    session=Depends(get_session),
) -> Response[PublicConsent]:
    """Update a consent by id."""
    async with atomic(session):
        service = ConsentService(session)
        consent = await service.update_consent(consent_id, schema)

    return Response(result=PublicConsent(**consent.dict()))
