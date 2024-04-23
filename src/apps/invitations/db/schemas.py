from sqlalchemy import Column, ForeignKey, String, Unicode
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from apps.shared.enums import ColumnCommentType
from infrastructure.database import Base


class InvitationSchema(Base):
    __tablename__ = "invitations"

    email = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    applet_id = Column(ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False)
    role = Column(String())
    key = Column(UUID(as_uuid=True))
    invitor_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status = Column(String())
    first_name = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    last_name = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    meta = Column(JSONB())
    nickname = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    user_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
