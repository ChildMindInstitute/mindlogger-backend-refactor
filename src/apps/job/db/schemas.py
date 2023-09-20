from sqlalchemy import Column, Enum, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import JSONB

from apps.job.constants import JobStatus
from infrastructure.database import Base


class JobSchema(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        Index(
            "unique_user_job_name",
            "creator_id",
            "name",
            unique=True,
        ),
    )

    name = Column(Text, nullable=False)
    creator_id = Column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(Enum(JobStatus, name="job_status"), nullable=False)
    details = Column(JSONB(), nullable=True)
