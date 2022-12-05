from sqlalchemy import Column, String

from infrastructure.database.base import Base


class AppletSchema(Base):
    __tablename__ = "applets"

    display_name = Column(String(length=100), unique=True)
    description = Column(String(length=100))
