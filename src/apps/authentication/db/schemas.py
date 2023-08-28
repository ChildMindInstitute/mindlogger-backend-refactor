from sqlalchemy import Column, DateTime, Enum, Text
from sqlalchemy.dialects.postgresql import UUID

from apps.authentication.domain.token import TokenPurpose
from infrastructure.database import Base


class TokenBlacklistSchema(Base):
    __tablename__ = "token_blacklist"

    jti = Column(Text(), index=True, unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    exp = Column(DateTime(), index=True, nullable=False)
    type = Column(Enum(TokenPurpose), nullable=False)
    rjti = Column(Text(), index=True, nullable=True)
