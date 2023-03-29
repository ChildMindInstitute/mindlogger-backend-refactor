from sqlalchemy import Boolean, Column, ForeignKey, String, Text

from infrastructure.database.base import Base


class AlertConfigSchema(Base):
    """This table is used as an alert configuration for a
    specific applet and specific activity item answer
    """

    __tablename__ = "alerts_configs"

    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_item_histories_id_version = Column(
        ForeignKey("activity_item_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    alert_message = Column(String(), nullable=False)
    specific_answer = Column(Text(), nullable=False)
    viewed = Column(Boolean(), nullable=False, default=True)


class AlertSchema(Base):
    """This table is used as responses to specific flow activity items"""

    __tablename__ = "alerts"

    alert_config_id = Column(
        ForeignKey("alerts_configs.id", ondelete="RESTRICT"),
        nullable=False,
    )
    respondent_id = Column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_watched = Column(Boolean(), nullable=False, default=False)
    applet_id = Column(
        ForeignKey("applets.id", ondelete="RESTRICT"),
        nullable=False,
    )
    activity_item_histories_id_version = Column(
        ForeignKey("activity_item_histories.id_version", ondelete="RESTRICT"),
        nullable=False,
    )
    alert_message = Column(String(), nullable=False)
    specific_answer = Column(Text(), nullable=False)
