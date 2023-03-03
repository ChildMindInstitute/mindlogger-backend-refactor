from sqlalchemy import Boolean, Column, ForeignKey, String

from infrastructure.database.base import Base

__all__ = ["UserWorkspaceSchema"]


class UserWorkspaceSchema(Base):
    __tablename__ = "users_workspaces"

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    workspace_name = Column(String(length=100), nullable=False, index=True)
    is_modified = Column(Boolean(), default=False)
