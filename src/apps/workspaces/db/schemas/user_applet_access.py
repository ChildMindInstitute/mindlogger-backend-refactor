from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.hybrid import hybrid_property

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

    @hybrid_property
    def respondent_nickname(self):
        return self.meta.get("nickname")

    @respondent_nickname.expression  # type: ignore[no-redef]
    def respondent_nickname(cls):
        return cls.meta[text("'nickname'")].astext

    @hybrid_property
    def respondent_secret_id(self):
        return self.meta.get("secretUserId")

    @respondent_secret_id.expression  # type: ignore[no-redef]
    def respondent_secret_id(cls):
        return cls.meta[text("'secretUserId'")].astext


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
