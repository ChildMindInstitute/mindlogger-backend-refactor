from apps.applets.domain import AppletHistory
from apps.shared.changes_generator import EMPTY_VALUES, BaseChangeGenerator


class AppletChangeService(BaseChangeGenerator):
    field_name_verbose_name_map = {
        "display_name": "Applet Name",
        "description": "Applet Description",
        "about": "About Applet Page",
        "image": "Applet Image",
        "watermark": "Applet Watermark",
        "report_server_ip": "Server URL",
        "report_public_key": "Public encryption key",
        # Ask better verbose name
        "report_recipients": "Email recipients",
        "report_include_user_id": "Include respondent in the Subject and Attachment",  # noqa E501
        # Where is this field
        "report_email_body": "Email Body",
        "stream_enabled": "Enable streaming of response data",
    }

    def compare(
        self, old_applet: AppletHistory | None, new_applet: AppletHistory
    ) -> list[str]:
        changes = []
        for (
            field_name,
            verbose_name,
        ) in self.field_name_verbose_name_map.items():
            old_value = getattr(old_applet, field_name) if old_applet else None
            new_value = getattr(new_applet, field_name)
            # First just check that something was changed
            if (
                old_value in EMPTY_VALUES
                and new_value in EMPTY_VALUES
                or new_value == old_value
            ):
                continue
            if isinstance(new_value, bool):
                changes.append(
                    self._change_text_generator.set_bool(
                        verbose_name, new_value
                    )
                )
            elif self._change_text_generator.is_considered_empty(new_value):
                changes.append(
                    self._change_text_generator.cleared_text(verbose_name),
                )
            elif self._change_text_generator.is_considered_empty(old_value):
                changes.append(
                    self._change_text_generator.changed_text(
                        verbose_name, new_value, is_initial=True
                    ),
                )
            else:
                changes.append(
                    self._change_text_generator.changed_text(
                        verbose_name, new_value
                    )
                )

        return changes
