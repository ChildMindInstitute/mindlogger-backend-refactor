from apps.shared.commands.domain import Patch


class PatchRegister:
    patches: list[Patch] | None = None

    @classmethod
    def register(
        cls,
        file_path: str,
        task_id: str,
        description: str,
        manage_session: bool,
    ):
        cls.patches = cls.patches or []
        # check if task_id already exist
        found_patch = next((p for p in cls.patches if p.task_id == task_id), None)
        if found_patch:
            raise ValueError(f"Patch with task_id {task_id} already exist")
        cls.patches.append(
            Patch(
                file_path=file_path,
                task_id=task_id,
                description=description,
                manage_session=manage_session,
            )
        )

    @classmethod
    def get_all(cls) -> list[Patch]:
        return cls.patches or []

    @classmethod
    def get_by_task_id(cls, task_id: str) -> Patch | None:
        if not cls.patches:
            return None
        # find patch by task_id
        found_patch = next((p for p in cls.patches if p.task_id == task_id), None)

        return found_patch
