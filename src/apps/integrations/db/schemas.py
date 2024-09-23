from sqlalchemy import Column, ForeignKey, Text, Unicode, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from infrastructure.database.base import Base

__all__ = ["IntegrationsSchema"]


class IntegrationsSchema(Base):
    __tablename__ = "integrations"
    __table_args__ = (
        UniqueConstraint(
            "applet_id",
            "type",
            name="_unique_applet_integration",
        ),
    )

    applet_id = Column(ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False, unique=False)
    type = Column(Text(), unique=False)
    configuration = Column(StringEncryptedType(Unicode, get_key), unique=False)
