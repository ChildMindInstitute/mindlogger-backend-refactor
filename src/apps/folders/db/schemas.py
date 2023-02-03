from sqlalchemy import Column, ForeignKey, String

from infrastructure.database import Base

__all__ = ["FolderSchema"]


class FolderSchema(Base):
    __tablename__ = "folders"

    creator_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    name = Column(String(255))
