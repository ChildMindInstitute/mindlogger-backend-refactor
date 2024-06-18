from sqlalchemy import Boolean, Column, ForeignKey, Unicode
from sqlalchemy.dialects.postgresql import JSONB
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
    workspace_name = Column(StringEncryptedType(Unicode, get_key), nullable=False, index=True)
    is_modified = Column(Boolean(), default=False)
    database_uri = Column(StringEncryptedType(Unicode, get_key))
    storage_type = Column(StringEncryptedType(Unicode, get_key))
    storage_access_key = Column(StringEncryptedType(Unicode, get_key))
    storage_secret_key = Column(StringEncryptedType(Unicode, get_key))
    storage_region = Column(StringEncryptedType(Unicode, get_key))
    storage_url = Column(StringEncryptedType(Unicode, get_key))
    storage_bucket = Column(StringEncryptedType(Unicode, get_key))
    use_arbitrary = Column(Boolean(), default=False)
    integrations = Column(JSONB(), default=dict())
