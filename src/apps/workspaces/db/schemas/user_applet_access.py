from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from apps.workspaces.domain.constants import UserPinRole
from infrastructure.database.base import Base

__all__ = ["UserAppletAccessSchema"]


class UserAppletAccessSchema(Base):
    __tablename__ = "user_applet_accesses"

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role = Column(String(length=20), nullable=False, index=True)
    owner_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    invitor_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    meta = Column(JSONB())
    is_pinned = Column(Boolean(), default=False)


class UserPinSchema(Base):
    __tablename__ = "user_pins"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "pinned_user_id",
            "owner_id",
            "role",
            name="user_pins_uq",
        ),
    )

    user_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    pinned_user_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    owner_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(Enum(UserPinRole, name="user_pin_role"), nullable=False)
