from sqlalchemy import Column, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID

from infrastructure.database import Base

__all__ = ["ActivityAssigmentSchema"]


class ActivityAssigmentSchema(Base):
    __tablename__ = "activity_assignments"

    activity_flow_id = Column(UUID(as_uuid=True), nullable=True)
    activity_id = Column(UUID(as_uuid=True), nullable=True)
    respondent_subject_id = Column(ForeignKey("subjects.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    target_subject_id = Column(ForeignKey("subjects.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)

    __table_args__ = (
        Index(
            "uq_activity_assignments_activity_respondent_target",
            "activity_id",
            "respondent_subject_id",
            "target_subject_id",
            unique=True,
        ),
        Index(
            "uq_activity_assignments_activity_flow_respondent_target",
            "activity_flow_id",
            "respondent_subject_id",
            "target_subject_id",
            unique=True,
        ),
    )
