from sqlalchemy import Column, ForeignKey, String

from infrastructure.database import Base, UTCDateTime

__all__ = ["FolderSchema"]


class FolderSchema(Base):
    __tablename__ = "folders"

    workspace_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    creator_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    name = Column(String(255))


class FolderAppletSchema(Base):
    __tablename__ = "folder_applets"

    folder_id = Column(ForeignKey("folders.id", ondelete="CASCADE"), nullable=False)
    applet_id = Column(ForeignKey("applets.id", ondelete="CASCADE"), nullable=False)
    pinned_at = Column(UTCDateTime(), nullable=True)
