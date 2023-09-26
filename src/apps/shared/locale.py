from config import settings


class I18N:
    def __init__(self, lang: str):
        self.lang: str = lang
        self.default: str = settings.default_language

    def translate(self, val: dict):
        if not val:
            return None
        try:
            return val[self.lang]
        except KeyError:
            if self.default in val:
                return val[self.default]
            return list(val.values())[0]
