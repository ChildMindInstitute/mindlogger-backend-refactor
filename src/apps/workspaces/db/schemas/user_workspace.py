from sqlalchemy import Boolean, Column, ForeignKey, String, Unicode
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from infrastructure.database.base import Base


class UserWorkspaceSchema(Base):
    __tablename__ = "users_workspaces"

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
        index=True,
    )
    workspace_name = Column(
        StringEncryptedType(Unicode, get_key), nullable=False, index=True
    )
    is_modified = Column(Boolean(), default=False)
    database_uri = Column(String())
    storage_type = Column(String())
    storage_access_key = Column(String())
    storage_secret_key = Column(String())
    storage_region = Column(String())
    storage_url = Column(String(), nullable=True, default=None)
    storage_bucket = Column(String(), nullable=True, default=None)
    use_arbitrary = Column(Boolean(), default=False)
