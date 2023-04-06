import asyncio
import enum
from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Callable,
    Type,
    Tuple,
    Optional,
    Any,
)

from pyld import (
    ContextResolver,
    jsonld,
)

from apps.jsonld_converter.errors import JsonLDNotSupportedError
from apps.shared.domain import InternalModel


class LdKeyword(str, enum.Enum):
    context = '@context'
    type = '@type'
    id = "@id"
    value = "@value"
    graph = "@graph"
    language = "@language"
    list = "@list"


class LdAttributeProcessor:
    """
    https://raw.githubusercontent.com/ChildMindInstitute/reproschema-context/master/context.json
    """

    TERMS = {
        'reproschema': [
            "http://schema.repronim.org/",
            "https://schema.repronim.org/",
            "https://raw.githubusercontent.com/ReproNim/reproschema/master/terms/",
            "https://raw.githubusercontent.com/ReproNim/reproschema/master/schemas/",
        ],
        'schema': ["http://schema.org/"],
        'skos': ["http://www.w3.org/2004/02/skos/core#"],
        "xsd": ["http://www.w3.org/2001/XMLSchema#"],
    }

    @classmethod
    def first(cls, obj: Any) -> Any:
        if isinstance(obj, list) and obj:
            return obj[0]

        return obj

    @classmethod
    def resolve_key(cls, attr: str) -> list[str]:
        term, attr = attr.split(':', 1)
        base_urls = cls.TERMS[term]
        keys = [url + attr for url in base_urls]

        return keys

    @classmethod
    def is_equal_term_val(cls, val, term_val):
        for _val in cls.resolve_key(term_val):
            if val == _val:
                return True
        return False

    @classmethod
    def get_key(cls, doc: dict, attr: str) -> str | None:
        keys = cls.resolve_key(attr)
        for key in keys:
            if key in doc:
                return key
        return None

    @classmethod
    def get_attr(cls, doc: dict, attr: str, *, drop=None):
        key = cls.get_key(doc, attr)
        if key:
            return doc[key]

    @classmethod
    def get_attr_single(cls, doc: dict, attr: str, *, drop: bool = False, ld_key: LdKeyword | None = None):
        key = cls.get_key(doc, attr)
        if key:
            res = doc[key]
            if isinstance(res, list) and res:
                res = res[0]
            if ld_key and isinstance(res, dict):
                res = res.get(ld_key)
            if drop and res is not None:
                del doc[key]

            return res

    @classmethod
    def get_attr_list(cls, doc: dict, attr: str, *, drop: bool = False) -> list | None:
        key = cls.get_key(doc, attr)
        if key and isinstance(obj_list := doc[key], list):
            if len(obj_list) == 1 and isinstance(obj_list[0], dict) and LdKeyword.list in obj_list[0]:
                obj_list = obj_list[0][LdKeyword.list]
            if drop:
                del doc[key]
            return obj_list

    @classmethod
    def get_attr_value(cls, doc: dict, attr: str, *, drop: bool = False):
        return cls.get_attr_single(doc, attr, drop=drop, ld_key=LdKeyword.value)

    @classmethod
    def get_translations(cls, doc: dict, term_attr: str, *, drop=False) -> dict[str, str] | None:
        key = cls.get_key(doc, term_attr)
        if key:
            res = cls._get_lang_formatted(doc[key])
            if drop:
                del doc[key]

            return res
        return None

    @classmethod
    def get_translation(cls, doc: dict, term_attr: str, lang: str, *, drop=False) -> str | None:
        items = cls.get_translations(doc, term_attr, drop=drop)
        if items:
            if val := items.get(lang):
                return val
            return next(iter(items.values()))

    @classmethod
    def _get_lang_formatted(cls, items: list[dict]) -> dict:
        res = {}
        for item in items:
            lang, val = item.get(LdKeyword.language), item.get(LdKeyword.value)
            if lang:
                res[lang] = val

        return res


class ContextResolverAwareMixin:
    document_loader: Optional[Callable] = None
    context_resolver: ContextResolver = None

    async def load_remote_doc(self, remote_doc: str) -> dict:
        assert self.document_loader is not None
        try:
            return await asyncio.to_thread(self.document_loader, remote_doc)
        except Exception as e:
            raise


class ContainsNestedMixin(ABC, ContextResolverAwareMixin):
    @classmethod
    @abstractmethod
    def get_supported_types(cls) -> list[Type["LdDocumentBase"]]:
        ...

    @classmethod
    def _get_supported(cls, doc: dict) -> Type["LdDocumentBase"] | None:
        for candidate in cls.get_supported_types():
            if candidate.supports(doc):
                return candidate
        return None

    async def load_supported_document(self, doc: str | dict, base_url) -> "LdDocumentBase":
        assert self.document_loader is not None
        assert self.context_resolver is not None

        if isinstance(doc, str):
            new_doc, base_url = await self._load_by_url(doc)
        elif LdKeyword.type not in doc:
            new_doc, base_url = await self._load_by_id(doc, base_url)
            # TODO override with original doc values?
        else:
            new_doc = doc

        type_ = self._get_supported(new_doc)
        if type_ is None:
            raise JsonLDNotSupportedError(new_doc)

        obj = type_(self.context_resolver, self.document_loader)
        await obj.load(new_doc, base_url)

        return obj

    async def _load_by_id(self, doc: dict, base_url: str) -> Tuple[dict, str]:
        doc_id = doc[LdKeyword.id]
        # TODO try load, try to fix url with base_url and id
        doc, base_url = await self._load_by_url(doc_id)
        return doc, base_url

    async def _load_by_url(self, remote_doc: str) -> Tuple[dict, str]:
        loaded = await self.load_remote_doc(remote_doc)  # TODO exceptions
        return loaded['document'], loaded['documentUrl'] or remote_doc


class CommonFieldsMixin:
    attr_processor: LdAttributeProcessor

    lang = 'en'

    def _get_ld_description(self, doc: dict, drop=False):
        return self.attr_processor.get_translations(doc, 'schema:description', drop=drop)

    def _get_ld_about(self, doc: dict, drop=False):
        return self.attr_processor.get_translations(doc, 'schema:about', drop=drop)

    def _get_ld_pref_label(self, doc: dict, drop=False):
        return self.attr_processor.get_translation(doc, 'skos:prefLabel', self.lang, drop=drop)

    def _get_ld_alt_label(self, doc: dict, drop=False):
        return self.attr_processor.get_translation(doc, 'skos:altLabel', self.lang, drop=drop)

    def _get_ld_version(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, 'schema:version', drop=drop)

    def _get_ld_schema_version(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, 'schema:schemaVersion', drop=drop)

    def _get_ld_image(self, doc: dict, drop=False):
        for keyword in [LdKeyword.id, LdKeyword.value]:
            if img := self.attr_processor.get_attr_single(doc, 'schema:image', drop=drop, ld_key=keyword):
                break
        if not img:
            img_obj = self.attr_processor.get_attr_single(doc, 'schema:image', drop=drop)
            if isinstance(img_obj, dict):
                img = self.attr_processor.get_attr_single(img_obj, 'schema:contentUrl', ld_key=LdKeyword.id)

        return img

    def _get_ld_properties_formatted(self, doc: dict, drop=False) -> dict:
        items = self.attr_processor.get_attr_list(doc, 'reproschema:addProperties', drop=drop)

        properties_by_id = {}
        if items:
            for item in items:
                _id = self.attr_processor.get_attr_single(item, 'reproschema:isAbout', ld_key=LdKeyword.id)
                _var = self.attr_processor.get_translation(item, 'reproschema:variableName', self.lang)
                _is_visible = self.attr_processor.get_attr_value(item, 'reproschema:isVis')
                _pref_label = self._get_ld_pref_label(item)
                _is_required = self.attr_processor.get_attr_value(item, 'reproschema:requiredValue')
                properties_by_id[_id] = {
                    'ld_variable_name': _var,
                    'ld_is_vis': _is_visible,
                    'ld_pref_label': _pref_label,
                    'ld_required_value': _is_required
                }

        return properties_by_id


class LdDocumentBase(ABC, ContextResolverAwareMixin):
    attr_processor: LdAttributeProcessor = LdAttributeProcessor()

    base_url: str | None = None
    ld_ctx: list | dict | str | None = None
    doc: dict | None = None
    doc_expanded: dict
    lang: str = 'en'

    ld_id: str | None = None
    ld_variable_name: str | None = None

    def __init__(self, context_resolver: ContextResolver, document_loader: Callable):
        self.context_resolver: ContextResolver = context_resolver
        self.document_loader = document_loader

    @classmethod
    @abstractmethod
    def supports(cls, doc: dict) -> bool:
        ...

    @abstractmethod
    def export(self) -> InternalModel:
        ...

    async def load(self, doc: dict, base_url: str | None = None):
        self.doc = doc
        self.base_url = base_url
        self.ld_ctx = doc.get(LdKeyword.context)
        expanded: list[dict] = await self._expand(doc, base_url)
        self.doc_expanded = expanded[0]
        self.ld_id = self.attr_processor.first(self.doc_expanded.get(LdKeyword.id))

    async def _expand(self, doc: dict, base_url: str | None = None):
        options = dict(
            base=base_url,
            contextResolver=self.context_resolver,
            documentLoader=self.document_loader,
        )
        return await asyncio.to_thread(jsonld.expand, doc, options)
