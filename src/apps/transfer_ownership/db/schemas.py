from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database import Base


class TransferSchema(Base):
    __tablename__ = "transfer_ownership"

    email = Column(String())
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )
    key = Column(UUID(as_uuid=True))
