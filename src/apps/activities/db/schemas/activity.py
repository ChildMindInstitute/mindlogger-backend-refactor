from sqlalchemy import REAL, Boolean, Column, ForeignKey, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from apps.activities.domain.response_type_config import PerformanceTaskType
from infrastructure.database.base import Base

__all__ = ["ActivitySchema", "ActivityHistorySchema"]


class _BaseActivitySchema:
    name = Column(String(length=100))
    description = Column(JSONB())
    splash_screen = Column(Text())
    image = Column(Text())
    show_all_at_once = Column(Boolean(), default=False)
    is_skippable = Column(Boolean(), default=False)
    is_reviewable = Column(Boolean(), default=False)
    response_is_editable = Column(Boolean(), default=False)
    order = Column(REAL())
    is_hidden = Column(Boolean(), default=False)
    scores_and_reports = Column(JSONB())
    subscale_setting = Column(JSONB())
    report_included_item_name = Column(Text(), nullable=True)
    extra_fields = Column(JSONB(), default=dict, server_default=text("'{}'::jsonb"))
    performance_task_type = Column(String(255), nullable=True)
    auto_assign = Column(Boolean(), default=True)

    @hybrid_property
    def is_performance_task(self) -> bool:
        return self.performance_task_type in PerformanceTaskType.get_values()

    @is_performance_task.expression  # type: ignore[no-redef]
    def is_performance_task(cls) -> bool:
        return func.coalesce(cls.performance_task_type, "").in_(PerformanceTaskType.get_values())


class ActivitySchema(Base, _BaseActivitySchema):
    __tablename__ = "activities"

    applet_id = Column(ForeignKey("applets.id", ondelete="RESTRICT"), nullable=False)


class ActivityHistorySchema(Base, _BaseActivitySchema):
    __tablename__ = "activity_histories"

    id = Column(UUID(as_uuid=True))
    id_version = Column(String(), primary_key=True)
    applet_id = Column(
        ForeignKey("applet_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )

    items = relationship(
        "ActivityItemHistorySchema",
        order_by="asc(ActivityItemHistorySchema.order)",
        lazy="noload",
    )
