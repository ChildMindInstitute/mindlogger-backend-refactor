from apps.job.domain import Job


class JobStatusError(Exception):
    def __init__(self, job: Job, *args, **kwargs):
        self.job = job
        super().__init__(*args, **kwargs)
