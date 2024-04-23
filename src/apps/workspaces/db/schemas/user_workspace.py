from sqlalchemy import Boolean, Column, ForeignKey, Unicode
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from apps.shared.enums import ColumnCommentType
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
        StringEncryptedType(Unicode, get_key), nullable=False, index=True, comment=ColumnCommentType.ENCRYPTED
    )
    is_modified = Column(Boolean(), default=False)
    database_uri = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    storage_type = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    storage_access_key = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    storage_secret_key = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    storage_region = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    storage_url = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    storage_bucket = Column(StringEncryptedType(Unicode, get_key), comment=ColumnCommentType.ENCRYPTED)
    use_arbitrary = Column(Boolean(), default=False)
