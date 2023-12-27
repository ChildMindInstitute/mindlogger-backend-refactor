import os

from pydantic import validator

from apps.shared.domain import InternalModel


class Patch(InternalModel):
    file_path: str
    task_id: str
    description: str
    manage_session: bool

    @validator("file_path")
    def validate_file_existance(cls, v):
        path = os.path.join(os.path.dirname(__file__), "patches", v)
        if not os.path.exists(path):
            raise ValueError("File does not exist")
        return v
