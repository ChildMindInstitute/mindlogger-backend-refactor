__all__ = ['AppletService']


class AppletService:
    INITIAL_VERSION = "1.0.0"
    VERSION_DIFFERENCE = 1

    def get_next_version(self, version: str | None = None):
        if not version:
            return self.INITIAL_VERSION
        return ".".join(
            list(str(int(version.replace(".", "")) + self.VERSION_DIFFERENCE))
        )

    def get_prev_version(self, version: str):
        int_version = int(version.replace(".", ""))
        if int_version < int(self.INITIAL_VERSION.replace(".", "")):
            return self.INITIAL_VERSION
        return ".".join(list(str(int_version - self.VERSION_DIFFERENCE)))
