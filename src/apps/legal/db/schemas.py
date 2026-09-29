from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database import Base


class LegalAcceptanceSchema(Base):
    """One row per acceptance of a legal document version. Append-only."""

    __tablename__ = "user_legal_acceptances"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    doc_type = Column(String(50), nullable=False)
    version = Column(String(50), nullable=False)
    accepted_at = Column(DateTime(), nullable=False)
    source = Column(String(50), nullable=False)
    client_source = Column(String(50), nullable=True)
    ip_address = Column(Text(), nullable=True)
    user_agent = Column(Text(), nullable=True)

    __table_args__ = (Index("ix_user_legal_acceptances_user_id_doc_type", "user_id", "doc_type"),)
