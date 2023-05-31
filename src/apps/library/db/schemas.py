from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database import Base


class LibrarySchema(Base):
    __tablename__ = "library"

    applet_id_version = Column(
        ForeignKey("applet_histories.id", ondelete="RESTRICT"), nullable=False
    )
