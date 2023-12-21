from apps.shared.commands.domain import PatchRegister


class Patch:
    patches: list[PatchRegister] | None = None

    @classmethod
    def register(self, patch: PatchRegister):
        self.patches = self.patches or []
        self.patches.append(patch)

    @classmethod
    def get_all(self):
        return self.patches or []

    @classmethod
    def get_all_by_task_id(self, task_id: str):
        if not self.patches:
            return []
        found_patches = [
            patch for patch in self.patches if patch.task_id == task_id
        ]
        # if found patches are more than 1, order by patch.order
        if len(found_patches) > 1:
            found_patches.sort(key=lambda patch: patch.order)
        return found_patches


Patch.register(
    PatchRegister(
        file_path="slider_tickmark_label.py",
        task_id="M2-3781",
        description="Slider tick marks and labels fix",
        order=1,
    )
)
