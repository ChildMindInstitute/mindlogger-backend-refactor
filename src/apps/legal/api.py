from fastapi import Body, Depends, Request

from apps.authentication.deps import get_current_user
from apps.legal.cache import MsaTestSettingsCache
from apps.legal.constants import AcceptanceSource
from apps.legal.domain import MsaAcceptRequest, MsaTestSettings, MsaVersion, PublicMsaStatus
from apps.legal.service import LegalAcceptanceService
from apps.shared.domain.response import Response
from apps.shared.exception import NotFoundError
from apps.users.domain import User
from config import settings
from infrastructure.database.core import atomic
from infrastructure.database.deps import get_session


async def msa_version_get() -> Response[MsaVersion]:
    """Current MSA version. Public, since signup happens before login."""
    return Response(result=MsaVersion(version=settings.legal.msa_version))


async def msa_status_get(
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[PublicMsaStatus]:
    """Whether the user still has to accept the MSA, and by when."""
    result = await LegalAcceptanceService(session).get_msa_status(user.id)
    return Response(result=PublicMsaStatus(**result.model_dump()))


async def msa_accept(
    request: Request,
    schema: MsaAcceptRequest = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[PublicMsaStatus]:
    """Accept the MSA from the prompt shown after login."""
    service = LegalAcceptanceService(session)
    async with atomic(session):
        await service.accept_msa_once(user.id, AcceptanceSource.LOGIN_PROMPT, request, schema.msa_version)
    result = await service.get_msa_status(user.id)
    return Response(result=PublicMsaStatus(**result.model_dump()))


async def msa_test_overrides_enabled() -> None:
    """The MSA test settings endpoints only exist where the flag is on (dev)."""
    if not settings.legal.msa_test_overrides_enabled:
        raise NotFoundError()


async def msa_test_settings_put(
    schema: MsaTestSettings = Body(...),
    user: User = Depends(get_current_user),
    session=Depends(get_session),
) -> Response[PublicMsaStatus]:
    """Set the logged-in user's own MSA test settings and return their MSA status under them."""
    await MsaTestSettingsCache().save(user.id, schema)
    result = await LegalAcceptanceService(session).get_msa_status(user.id)
    return Response(result=PublicMsaStatus(**result.model_dump()))
