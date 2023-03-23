class JsonLDBaseError(Exception):
    ...


class JsonLDStructureError(JsonLDBaseError):
    ...


class JsonLDNotSupportedError(JsonLDBaseError):
    def __init__(self, doc: dict, *args, **kwargs) -> None:
        super().__init__('Document not supported', doc, *args, **kwargs)
        self.doc = doc
