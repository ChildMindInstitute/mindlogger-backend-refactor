import uuid

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database.base import Base


class ConsentSchema(Base):
    __tablename__ = "consents"

    user_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    is_ready_share_data = Column(Boolean(), default=False)
    is_ready_share_media_data = Column(Boolean(), default=False)


class MlLorisUserRelationshipSchema(Base):
    __tablename__ = "ml_loris_user_relationship"

    ml_user_uuid = Column(UUID(as_uuid=True), primary_key=True, default=lambda: uuid.uuid4())
    loris_user_id = Column(String, unique=True, nullable=False)
