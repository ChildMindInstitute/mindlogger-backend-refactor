import datetime
import uuid

import pytz
from fastapi import Request

from apps.legal.constants import (
    MSA_DAY_ROLLOVER_HOURS,
    MSA_DAY_TIMEZONE,
    AcceptanceSource,
    LegalDocType,
    MsaStatus,
)
from apps.legal.crud import LegalAcceptancesCRUD
from apps.legal.domain import LegalAcceptance, LegalAcceptanceCreate, MsaSettings, MsaStatusResult
from apps.legal.errors import MSAVersionOutdatedError
from apps.users.cruds.user import UsersCRUD
from config import settings
from infrastructure.http.deps import get_optional_mindlogger_content_source


def msa_today(now: datetime.datetime | None = None) -> datetime.date:
    """Today's date for the MSA rules: the day starts at 3am Eastern, whatever the user's time zone."""
    now = now or datetime.datetime.now(datetime.timezone.utc)
    eastern = now.astimezone(pytz.timezone(MSA_DAY_TIMEZONE))
    return (eastern - datetime.timedelta(hours=MSA_DAY_ROLLOVER_HOURS)).date()


class LegalAcceptanceService:
    def __init__(self, session):
        self.session = session

    async def accept_msa(
        self, user_id: uuid.UUID, source: AcceptanceSource, request: Request, version: str
    ) -> LegalAcceptance:
        """Record that the user accepted the given MSA version, if it is still the current one."""
        msa = await self.get_msa_settings(user_id)
        if version != msa.version:
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
        msa = await self.get_msa_settings(user_id)
        version, effective_from = msa.version, msa.effective_from
        today = msa_today()
        if effective_from is None or today < effective_from:
            return MsaStatusResult(status=MsaStatus.ACCEPTED, version=version)

        if await LegalAcceptancesCRUD(self.session).has_accepted(user_id, LegalDocType.MSA, version):
            return MsaStatusResult(status=MsaStatus.ACCEPTED, version=version)

        if not await self._is_existing_admin_user(user_id, msa.signup_cutoff or effective_from):
            return MsaStatusResult(status=MsaStatus.REQUIRED, version=version)

        # The start day counts, so 60 grace days end on effective date + 59
        deadline = effective_from + datetime.timedelta(days=msa.grace_days - 1)
        # The deadline day is still grace; past it the date is still returned so admin can say when it ended
        status = MsaStatus.GRACE if today <= deadline else MsaStatus.REQUIRED
        return MsaStatusResult(status=status, version=version, deadline=deadline)

    async def get_msa_settings(self, user_id: uuid.UUID) -> MsaSettings:
        """The MSA settings that apply to this user."""
        return MsaSettings(
            version=settings.legal.msa_version,
            effective_from=settings.legal.msa_effective_from,
            grace_days=settings.legal.msa_grace_days,
            signup_cutoff=settings.legal.msa_grace_signup_cutoff,
        )

    async def _is_existing_admin_user(self, user_id: uuid.UUID, cutoff: datetime.date | None) -> bool:
        """Grace period goes to users who accepted an earlier MSA version or signed up before the cutoff."""
        if await LegalAcceptancesCRUD(self.session).has_accepted(user_id, LegalDocType.MSA):
            return True
        created_at = await UsersCRUD(self.session).get_created_at(user_id)
        if cutoff is None or created_at is None:
            return False
        # Signing up on the cutoff day itself does not count; days start at 3am Eastern, like the deadline
        return msa_today(created_at.replace(tzinfo=datetime.timezone.utc)) < cutoff
