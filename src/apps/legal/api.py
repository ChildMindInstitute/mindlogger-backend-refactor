from apps.legal.domain import MsaVersion
from apps.shared.domain.response import Response
from config import settings


async def msa_version_get() -> Response[MsaVersion]:
    """Current MSA version. Public, since signup happens before login."""
    return Response(result=MsaVersion(version=settings.legal.msa_version))
