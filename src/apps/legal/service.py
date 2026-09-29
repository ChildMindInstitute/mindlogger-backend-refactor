import datetime
import uuid

from fastapi import Request

from apps.legal.constants import AcceptanceSource, LegalDocType
from apps.legal.crud import LegalAcceptancesCRUD
from apps.legal.domain import LegalAcceptance, LegalAcceptanceCreate
from config import settings


class LegalAcceptanceService:
    def __init__(self, session):
        self.session = session

    async def accept_msa(self, user_id: uuid.UUID, source: AcceptanceSource, request: Request) -> LegalAcceptance:
        """Record that the user accepted the current MSA version."""
        data = LegalAcceptanceCreate(
            user_id=user_id,
            doc_type=LegalDocType.MSA,
            version=settings.legal.msa_version,
            accepted_at=datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None),
            source=source,
            client_source=request.headers.get("mindlogger-content-source"),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return await LegalAcceptancesCRUD(self.session).create(data)
