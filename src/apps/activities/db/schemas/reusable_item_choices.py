from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint

from infrastructure.database.base import Base


class ReusableItemChoiceSchema(Base):
    __tablename__ = "reusable_item_choices"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "token_name",
            "token_value",
            "input_type",
            name="_unique_item_choices",
        ),
    )

    user_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    token_name = Column(String(length=100), nullable=False)
    token_value = Column(Integer(), nullable=False)
    input_type = Column(String(length=20), nullable=False)
