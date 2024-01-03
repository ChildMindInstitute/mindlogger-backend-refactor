from apps.shared.commands.domain import Patch


class PatchRegister:
    patches: list[Patch] | None = None

    @classmethod
    def register(
        self,
        file_path: str,
        task_id: str,
        description: str,
        manage_session: bool,
    ):
        self.patches = self.patches or []
        # check if task_id already exist
        found_patch = next(
            (p for p in self.patches if p.task_id == task_id), None
        )
        if found_patch:
            raise ValueError(f"Patch with task_id {task_id} already exist")
        self.patches.append(
            Patch(
                file_path=file_path,
                task_id=task_id,
                description=description,
                manage_session=manage_session,
            )
        )

    @classmethod
    def get_all(self):
        return self.patches or []

    @classmethod
    def get_by_task_id(self, task_id: str):
        if not self.patches:
            return []
        # find patch by task_id
        found_patch = next(
            (p for p in self.patches if p.task_id == task_id), None
        )

        return found_patch
