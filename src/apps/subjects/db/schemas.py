from sqlalchemy import Column, ForeignKey, Index, String, Unicode
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from infrastructure.database.base import Base

__all__ = ["SubjectSchema", "SubjectRelationSchema"]


class SubjectSchema(Base):
    __tablename__ = "subjects"
    applet_id = Column(ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False)
    creator_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    user_id = Column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    email = Column(StringEncryptedType(Unicode, get_key), default=None)
    first_name = Column(StringEncryptedType(Unicode, get_key), nullable=False)
    last_name = Column(StringEncryptedType(Unicode, get_key), nullable=False)
    nickname = Column(StringEncryptedType(Unicode, get_key), default=None, nullable=True)
    tag = Column(String, default=None, nullable=True)
    secret_user_id = Column(String, nullable=False)
    language = Column(String(length=5))
    __table_args__ = (
        Index(
            None,
            "user_id",
            "applet_id",
            unique=True,
        ),
    )


class SubjectRelationSchema(Base):
    __tablename__ = "subject_relations"
    source_subject_id = Column(
        ForeignKey("subjects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    target_subject_id = Column(
        ForeignKey("subjects.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    relation = Column(String(length=20), nullable=False)

    __table_args__ = (
        Index(
            "uq_subject_relations_source_target",
            "source_subject_id",
            "target_subject_id",
            unique=True,
        ),
    )
