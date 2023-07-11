class JsonLDBaseError(Exception):
    ...


class JsonLDStructureError(JsonLDBaseError):
    def __init__(self, message, doc: dict, *args, **kwargs):
        super().__init__(message, doc, *args, **kwargs)
        self.doc = doc


class JsonLDNotSupportedError(JsonLDBaseError):
    def __init__(self, doc: dict, *args, **kwargs):
        super().__init__("Document not supported", doc, *args, **kwargs)
        self.doc = doc


class JsonLDLoaderError(JsonLDBaseError):
    def __init__(self, doc_url: str, *args, **kwargs):
        super().__init__("Document loading error", doc_url, *args, **kwargs)
        self.doc_url = doc_url


class JsonLDProcessingError(JsonLDBaseError):
    def __init__(self, message, doc: dict | str, *args, **kwargs):
        message = message or "Document processing error"
        super().__init__(message, doc, *args, **kwargs)
        self.doc = doc


class ConditionalLogicError(JsonLDBaseError):
    def __init__(self, expression=None, *args, **kwargs):
        message = "Conditional logic processing error"
        super().__init__(message, expression, *args, **kwargs)
        self.expression = expression


class ConditionalLogicParsingError(JsonLDBaseError):
    ...


class SubscaleParsingError(JsonLDBaseError):
    ...
