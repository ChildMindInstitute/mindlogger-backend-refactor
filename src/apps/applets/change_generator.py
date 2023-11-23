from apps.applets.domain import AppletHistory
from apps.shared.changes_generator import BaseChangeGenerator
from apps.shared.domain.base import to_camelcase


class AppletChangeGenerator(BaseChangeGenerator):
    def generate_applet_changes(
        self, new_applet: AppletHistory, old_applet: AppletHistory
    ) -> list[str]:
        changes = []
        for field, old_value in old_applet.dict().items():
            new_value = getattr(new_applet, field, None)
            if not any([old_value, new_value]):
                continue
            if new_value == old_value:
                continue
            if self._change_text_generator.is_considered_empty(new_value):
                changes.append(
                    self._change_text_generator.cleared_text(
                        to_camelcase(field)
                    ),
                )
            elif self._change_text_generator.is_considered_empty(old_value):
                changes.append(
                    self._change_text_generator.filled_text(
                        to_camelcase(field), new_value
                    ),
                )
            else:
                changes.append(
                    self._change_text_generator.changed_text(
                        f"Applet {field}", new_value
                    )
                    if field not in ["about", "description"]
                    else f"Applet {to_camelcase(field)} updated: {self._change_text_generator.changed_dict(old_value, new_value)}."  # noqa: E501
                )

        return changes
