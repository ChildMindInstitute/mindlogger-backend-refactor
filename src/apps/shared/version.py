INITIAL_VERSION = "1.0.0"
VERSION_DIFFERENCE = 1


def get_next_version(version: str | None = None):
    if not version:
        return INITIAL_VERSION
    return ".".join(
        list(str(int(version.replace(".", "")) + VERSION_DIFFERENCE))
    )


def get_prev_version(version: str):
    int_version = int(version.replace(".", ""))
    if int_version < int(INITIAL_VERSION.replace(".", "")):
        return INITIAL_VERSION
    return ".".join(list(str(int_version - VERSION_DIFFERENCE)))
