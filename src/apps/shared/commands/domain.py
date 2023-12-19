from apps.shared.domain import InternalModel


class PatchRegister(InternalModel):
    file_path: str
    task_id: str
    description: str
    order: int | None
