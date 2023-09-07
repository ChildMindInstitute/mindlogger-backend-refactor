from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from broker import broker

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)
