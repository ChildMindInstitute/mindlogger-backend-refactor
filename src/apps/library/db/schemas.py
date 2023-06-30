from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY

from infrastructure.database import Base


class LibrarySchema(Base):
    __tablename__ = "library"

    applet_id_version = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    keywords = Column(ARRAY(String))
    search_keywords = Column(ARRAY(String))


# class Cart(Base):
#     __tablename__ = "cart"

#     user_id = Column(
#         ForeignKey("users.id", ondelete="RESTRICT"),
#         nullable=True,
#         unique=True,
#     )
