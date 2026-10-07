import datetime
import uuid

from apps.legal.constants import AcceptanceSource, LegalDocType, MsaStatus
from apps.shared.domain import InternalModel, PublicModel


class LegalAcceptanceCreate(InternalModel):
    user_id: uuid.UUID
    doc_type: LegalDocType
    version: str
    accepted_at: datetime.datetime
    source: AcceptanceSource
    client_source: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None


class LegalAcceptance(LegalAcceptanceCreate):
    id: uuid.UUID


class MsaVersion(PublicModel):
    version: str


class MsaStatusResult(InternalModel):
    status: MsaStatus
    version: str
    deadline: datetime.date | None = None


class PublicMsaStatus(PublicModel):
    status: MsaStatus
    version: str
    deadline: datetime.date | None = None


class MsaAcceptRequest(PublicModel):
    msa_version: str
