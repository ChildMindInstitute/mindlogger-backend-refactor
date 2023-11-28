from sqlalchemy import Column, ForeignKey, String, Unicode
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from apps.transfer_ownership.constants import TransferOwnershipStatus
from infrastructure.database import Base


class TransferSchema(Base):
    __tablename__ = "transfer_ownership"

    email = Column(StringEncryptedType(Unicode, get_key))
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )
    key = Column(UUID(as_uuid=True))
    status = Column(String(), server_default=TransferOwnershipStatus.PENDING)
