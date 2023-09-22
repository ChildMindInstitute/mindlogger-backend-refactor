import enum


class JobStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    success = "success"
    error = "error"
    retry = "retry"
