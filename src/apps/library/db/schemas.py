from sqlalchemy import ARRAY, Column, ForeignKey, String

from infrastructure.database import Base


class LibrarySchema(Base):
    __tablename__ = "library"

    applet_id_version = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    keywords = Column(ARRAY(String))
