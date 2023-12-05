from sqlalchemy import Boolean, Column, ForeignKey

from infrastructure.database.base import Base


class ConsentSchema(Base):
    __tablename__ = "consents"

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    is_ready_share_data = Column(Boolean(), default=False)
    is_ready_share_media_data = Column(Boolean(), default=False)
