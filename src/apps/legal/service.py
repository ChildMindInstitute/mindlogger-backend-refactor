import datetime
import uuid

from fastapi import Request

from apps.legal.constants import AcceptanceSource, LegalDocType, MsaStatus
from apps.legal.crud import LegalAcceptancesCRUD
from apps.legal.domain import LegalAcceptance, LegalAcceptanceCreate, MsaStatusResult
from apps.legal.errors import MSAVersionOutdatedError
from apps.users.cruds.user import UsersCRUD
from config import settings
from infrastructure.http.deps import get_optional_mindlogger_content_source


class LegalAcceptanceService:
    def __init__(self, session):
        self.session = session

    async def accept_msa(
        self, user_id: uuid.UUID, source: AcceptanceSource, request: Request, version: str
    ) -> LegalAcceptance:
        """Record that the user accepted the given MSA version, if it is still the current one."""
        if version != settings.legal.msa_version:
            raise MSAVersionOutdatedError()
        data = LegalAcceptanceCreate(
            user_id=user_id,
            doc_type=LegalDocType.MSA,
            version=version,
            accepted_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
            source=source,
            client_source=await get_optional_mindlogger_content_source(request),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return await LegalAcceptancesCRUD(self.session).create(data)

    async def accept_msa_once(
        self, user_id: uuid.UUID, source: AcceptanceSource, request: Request, version: str
    ) -> None:
        """Accept the MSA unless this version is already accepted, so repeat clicks make one row."""
        if not await LegalAcceptancesCRUD(self.session).has_accepted(user_id, LegalDocType.MSA, version):
            await self.accept_msa(user_id, source, request, version)

    async def get_msa_status(self, user_id: uuid.UUID) -> MsaStatusResult:
        """Whether the user has accepted the current MSA, is in the grace period, or must accept now."""
        version = settings.legal.msa_version
        effective_from = settings.legal.msa_effective_from
        today = datetime.datetime.now(datetime.timezone.utc).date()
        if effective_from is None or today < effective_from:
            return MsaStatusResult(status=MsaStatus.ACCEPTED, version=version)

        if await LegalAcceptancesCRUD(self.session).has_accepted(user_id, LegalDocType.MSA, version):
            return MsaStatusResult(status=MsaStatus.ACCEPTED, version=version)

        deadline = effective_from + datetime.timedelta(days=settings.legal.msa_grace_days)
        if today < deadline and await self._is_existing_admin_user(user_id):
            return MsaStatusResult(status=MsaStatus.GRACE, version=version, deadline=deadline)

        return MsaStatusResult(status=MsaStatus.REQUIRED, version=version)

    async def _is_existing_admin_user(self, user_id: uuid.UUID) -> bool:
        """Grace period goes to users who accepted an earlier MSA version or signed up before the cutoff."""
        if await LegalAcceptancesCRUD(self.session).has_accepted(user_id, LegalDocType.MSA):
            return True
        cutoff = settings.legal.msa_grace_signup_cutoff or settings.legal.msa_effective_from
        created_at = await UsersCRUD(self.session).get_created_at(user_id)
        # Signing up on the cutoff day itself does not count
        return cutoff is not None and created_at is not None and created_at.date() < cutoff
