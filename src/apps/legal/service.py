import datetime
import uuid

from fastapi import Request

from apps.legal.constants import AcceptanceSource, LegalDocType
from apps.legal.crud import LegalAcceptancesCRUD
from apps.legal.domain import LegalAcceptance, LegalAcceptanceCreate
from apps.legal.errors import MSAVersionOutdatedError
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
