from sqlalchemy import Boolean, Column, ForeignKey, String

from infrastructure.database.base import Base


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
    database_uri = Column(String())
    storage_type = Column(String())
    storage_access_key = Column(String())
    storage_secret_key = Column(String())
    storage_region = Column(String())
    storage_url = Column(String(), nullable=True, default=None)
    storage_bucket = Column(String(), nullable=True, default=None)
    use_arbitrary = Column(Boolean(), default=False)
