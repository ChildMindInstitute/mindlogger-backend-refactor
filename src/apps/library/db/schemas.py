from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

from infrastructure.database import Base


class LibrarySchema(Base):
    __tablename__ = "library"

    applet_id_version = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    keywords = Column(ARRAY(String), nullable=False, server_default="{}")
    search_keywords = Column(ARRAY(String), nullable=False, server_default="{}")


class CartSchema(Base):
    __tablename__ = "cart"

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        unique=True,
    )
    cart_items = Column(JSONB())
