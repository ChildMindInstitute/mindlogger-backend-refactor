from sqlalchemy import Column, ForeignKey, LargeBinary, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from infrastructure.database import Base


class InvitationSchema(Base):
    __tablename__ = "invitations"

    email = Column(String())
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )
    role = Column(String())
    key = Column(UUID(as_uuid=True))
    invitor_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status = Column(String())
    first_name = Column(LargeBinary(length=100), default=None)
    last_name = Column(LargeBinary(length=100), default=None)
    meta = Column(JSONB())
