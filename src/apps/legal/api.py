from fastapi import Depends

from apps.authentication.deps import get_current_user
from apps.legal.domain import MsaVersion, PublicMsaStatus
from apps.legal.service import LegalAcceptanceService
from apps.shared.domain.response import Response
from apps.users.domain import User
from config import settings
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
