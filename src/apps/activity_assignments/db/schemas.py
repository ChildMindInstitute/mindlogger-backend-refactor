from sqlalchemy import Column, ForeignKey

from infrastructure.database import Base

__all__ = ["ActivityAssigmentSchema"]


class ActivityAssigmentSchema(Base):
    __tablename__ = "activity_assignments"

    activity_flow_id = Column(ForeignKey("flows.id", ondelete="RESTRICT"), nullable=True)
    activity_id = Column(ForeignKey("activities.id", ondelete="RESTRICT"), nullable=True)
    respondent_subject_id = Column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
    target_subject_id = Column(ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False)
