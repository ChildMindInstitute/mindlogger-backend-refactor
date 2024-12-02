from gettext import gettext as _

from apps.shared.exception import NotFoundError


class SecretIDUniqueViolationError(Exception):
    pass


class AppletUserViolationError(Exception): ...


class SubjectNotFoundError(NotFoundError):
    message_is_template: bool = True
    message = _("Subject with id {subject_id} not found")
