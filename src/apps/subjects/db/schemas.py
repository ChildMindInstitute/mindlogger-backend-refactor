from sqlalchemy import Column, ForeignKey, String

from infrastructure.database.base import Base

__all__ = ["SubjectSchema", "SubjectRespondentSchema"]


class SubjectSchema(Base):
    __tablename__ = "subjects"
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False
    )
    # todo: tbd (why so short)
    email = Column(String(length=56), unique=True)
    creator_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
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
