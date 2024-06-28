import uuid

from sqlalchemy import (
    ARRAY,
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Index,
    String,
    Unicode,
    UniqueConstraint,
    case,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from apps.workspaces.domain.constants import UserPinRole
from infrastructure.database.base import Base

__all__ = ["UserAppletAccessSchema"]


class UserAppletAccessSchema(Base):
    __tablename__ = "user_applet_accesses"

    user_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    role = Column(String(length=20), nullable=False, index=True)
    owner_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    invitor_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    meta = Column(JSONB())
    nickname = Column(StringEncryptedType(Unicode, get_key))
    title = Column(StringEncryptedType(Unicode, get_key))

    is_pinned = Column(Boolean(), default=False)
    __table_args__ = (
        Index(
            "unique_user_applet_role",
            "user_id",
            "applet_id",
            "role",
            unique=True,
        ),
    )

    @hybrid_property
    def respondent_nickname(self):
        return self.nickname

    @respondent_nickname.expression  # type: ignore[no-redef]
    def respondent_nickname(cls):
        return cls.nickname

    @hybrid_property
    def respondent_secret_id(self):
        return self.meta.get("secretUserId")

    @respondent_secret_id.expression  # type: ignore[no-redef]
    def respondent_secret_id(cls):
        return cls.meta[text("'secretUserId'")].astext

    @hybrid_property
    def legacy_profile_id(self):
        return self.meta.get("legacyProfileId")

    @legacy_profile_id.expression  # type: ignore[no-redef]
    def legacy_profile_id(cls):
        return cls.meta[text("'legacyProfileId'")].astext

    @hybrid_property
    def reviewer_subjects(self):
        items = self.meta.get("subjects") or []
        return [uuid.UUID(itm) for itm in items]

    @reviewer_subjects.expression  # type: ignore[no-redef]
    def reviewer_subjects(cls):
        _field = cls.meta[text("'subjects'")]
        _subjects_jsonb = case(
            (
                func.jsonb_typeof(_field) == text("'array'"),
                _field,
            ),
            else_=text("'[]'::jsonb"),
        )
        return func.array(
            select(func.jsonb_array_elements_text(_subjects_jsonb)).correlate(UserAppletAccessSchema).scalar_subquery()
        ).cast(ARRAY(UUID))


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

    user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    pinned_user_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    pinned_subject_id = Column(ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True)
    owner_id = Column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(UserPinRole, name="user_pin_role"), nullable=False)
