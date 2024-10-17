import enum


class JobStatus(enum.StrEnum):
    pending = "pending"
    in_progress = "in_progress"
    success = "success"
    error = "error"
    retry = "retry"
