from enum import Enum


class PeriodicityType(str, Enum):
    once = "ONCE"
    daily = "DAILY"
    weekly = "WEEKLY"
    weekdays = "WEEKDAYS"
    monthly = "MONTHLY"


class TimerType(str, Enum):
    not_set = "NOT_SET"
    timer = "TIMER"
    idle = "IDLE"
