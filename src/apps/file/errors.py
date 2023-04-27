from apps.shared.enums import Language
from apps.shared.exception import NotFoundError


class FileNotFoundError(NotFoundError):
    messages = {
        Language.ENGLISH: "File not found."
    }
