from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from apps.authentication.domain.token import TokenPurpose
from infrastructure.database import Base


class TokenBlacklistSchema(Base):
    __tablename__ = "token_blacklist"

    jti = Column(Text(), index=True, unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    exp = Column(DateTime(), index=True, nullable=False)
    type = Column(Enum(TokenPurpose, name="token_purpose"), nullable=False)
    rjti = Column(Text(), index=True, nullable=True)


class RecoveryCodeSchema(Base):
    __tablename__ = "recovery_codes"

    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    code_hash = Column(Text(), nullable=False)
    code_encrypted = Column(Text(), nullable=False)
    used = Column(Boolean(), default=False, server_default="false", nullable=False)
    used_at = Column(DateTime(), nullable=True)
