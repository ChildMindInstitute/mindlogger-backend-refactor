from sqlalchemy import Column, String, ForeignKey, Integer, Table

from infrastructure.database.base import Base


class AppletSchema(Base):
    __tablename__ = "applets"

    name = Column(String(length=100))  # unique=True ?
