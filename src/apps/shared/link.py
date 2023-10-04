import uuid

from apps.shared.exception import ValidationError


def convert_link_key(key: str) -> uuid.UUID:
    """
    Convert legacy public links to uuid
    """
    try:
        if len(key) == 18:
            # legacy link
            return uuid.UUID(f"{key}-{'0' * 4}-{'0' * 12}")
        else:
            return uuid.UUID(key)
    except ValueError:
        raise ValidationError()
