from sqlalchemy import Column, ForeignKey, Index, String, Unicode
from sqlalchemy_utils import StringEncryptedType

from apps.shared.encryption import get_key
from infrastructure.database.base import Base

__all__ = ["SubjectSchema", "SubjectRespondentSchema"]


class SubjectSchema(Base):
    __tablename__ = "subjects"
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )
    creator_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    email = Column(StringEncryptedType(Unicode, get_key), default=None)
    first_name = Column(StringEncryptedType(Unicode, get_key), nullable=False)
    last_name = Column(StringEncryptedType(Unicode, get_key), nullable=False)
    nickname = Column(
        StringEncryptedType(Unicode, get_key), default=None, nullable=True
    )
    secret_user_id = Column(String, nullable=False)
    language = Column(String(length=5))
    __table_args__ = (
        Index(
            "unique_subject_user_applet",
            "user_id",
            "applet_id",
            unique=True,
        ),
    )


class SubjectRespondentSchema(Base):
    __tablename__ = "subject_respondents"
    respondent_access_id = Column(
        ForeignKey("user_applet_accesses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    subject_id = Column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False
    )
    relation = Column(String(length=20), unique=True)
