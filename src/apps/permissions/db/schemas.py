from sqlalchemy import Column, String, ForeignKey, Integer, Table
from enum import Enum
# from sqlalchemy.orm import declarative_base, relationship

from infrastructure.database.base import Base
from apps.users.db.schemas import UserSchema
from apps.applets.db.schemas import AppletSchema


class Role(str, Enum):
    ADMIN = "admin"
    CONTENT_MANAGER = "content manager"
    DATA_MANAGER = "data manager"
    CASE_MANAGER = "case manager"
    # USERS_MANAGER = "users manager"
    RESPONDENTS_MANAGER = "respondents manager"
    REVIEWERS_MANAGER = "reviewers manager"
    MANAGERS_MANAGER = "managers manager"
    REVIEWER = "reviewer"
    RESPONDENT = "respondent"


class UserAppletAccessSchema(Base):
    __tablename__ = "user_applet_accesses"

    user_id = Column(UserSchema, ForeignKey("users.id"), primary_key=True)
    applet_id = Column(AppletSchema, ForeignKey("applets.id"), primary_key=True)
    role = Column(Role)
