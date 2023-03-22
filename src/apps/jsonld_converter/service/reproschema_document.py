import asyncio
import enum
from abc import (
    ABC,
    abstractmethod,
)
from copy import deepcopy
from typing import (
    Callable,
    Type,
    Tuple,
    Optional,
    Any,
)

from apps.activities.domain.activity_create import ActivityCreate
from apps.applets.domain.applet_create import AppletCreate
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
    TERMS = {
        'reproschema': [
            "http://schema.repronim.org/",
            "https://raw.githubusercontent.com/ReproNim/reproschema/master/terms/",
            "https://raw.githubusercontent.com/ReproNim/reproschema/master/schemas/",
        ],
        'schema': ["http://schema.org/"],
        'skos': ["http://www.w3.org/2004/02/skos/core#"],
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
    def get_key(cls, doc: dict, attr: str) -> str | None:
        keys = cls.resolve_key(attr)
        for key in keys:
            if key in doc:
                return key
        return None

    @classmethod
    def get_attr(cls, doc: dict, attr: str):
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
    def get_lang_formatted(cls, items: list[dict]) -> dict:
        res = {}
        for item in items:
            lang, val = item.get(LdKeyword.language), item.get(LdKeyword.value)
            if lang:
                res[lang] = val

        return res

    @classmethod
    def get_attr_value(cls, doc: dict, attr: str, *, drop: bool = False):
        return cls.get_attr_single(doc, attr, drop=drop, ld_key=LdKeyword.value)

    @classmethod
    def get_translations(cls, doc: dict, term_attr: str, *, drop=False) -> dict[str, str] | None:
        key = cls.get_key(doc, term_attr)
        if key:
            res = cls.get_lang_formatted(doc[key])
            if drop:
                del doc[key]

            return res
        return None


class ContextResolverAwareMixin:
    document_loader: Optional[Callable] = None
    context_resolver: ContextResolver = None

    async def load_remote_doc(self, remote_doc: str) -> dict:
        assert self.document_loader is not None
        return await asyncio.to_thread(self.document_loader, remote_doc)


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
            raise JsonLDNotSupportedError(f'Document not supported', doc)

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
    ld_pref_label: str | None = None
    ld_alt_label: str | None = None
    ld_description: dict[str, str] | None = None
    ld_about: dict[str, str] | None = None
    ld_schema_version: str | None = None
    ld_version: str | None = None
    ld_image: str | None = None

    def _get_ld_description(self, doc: dict, drop=False):
        return self.attr_processor.get_translations(doc, 'schema:description', drop=drop)

    def _get_ld_about(self, doc: dict, drop=False):
        return self.attr_processor.get_translations(doc, 'schema:about', drop=drop)

    def _get_ld_pref_label(self, doc: dict, drop=False):
        items = self.attr_processor.get_translations(doc, 'skos:prefLabel', drop=drop)
        if items:
            if val := items.get(self.lang):
                return val
            return next(iter(items.values()))

    def _get_ld_alt_label(self, doc: dict, drop=False):
        items = self.attr_processor.get_translations(doc, 'skos:altLabel', drop=drop)
        if items:
            if val := items.get(self.lang):
                return val
            return next(iter(items.values()))

    def _get_ld_version(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, 'schema:version', drop=drop)

    def _get_ld_schema_version(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, 'schema:schemaVersion', drop=drop)

    def _get_ld_image(self, doc: dict, drop=False):
        for keyword in [LdKeyword.id, LdKeyword.value]:
            if img := self.attr_processor.get_attr_single(doc, 'schema:image', drop=drop, ld_key=keyword):
                break
        return img


class LdDocumentBase(ABC, ContextResolverAwareMixin):
    attr_processor: LdAttributeProcessor = LdAttributeProcessor()

    base_url: str | None = None
    ld_ctx: list | dict | str | None = None
    doc: dict | None = None
    doc_expanded: dict
    lang: str = 'en'

    ld_id: str | None = None

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

        )
        return await asyncio.to_thread(jsonld.expand, doc, options)


class ReproActivity(LdDocumentBase, ContainsNestedMixin, CommonFieldsMixin):

    @classmethod
    def supports(cls, doc: dict) -> bool:
        ld_types = [
            'reproschema:Activity',
            *cls.attr_processor.resolve_key('reproschema:Activity')
        ]
        return doc.get(LdKeyword.type) in ld_types

    @classmethod
    def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
        return []

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)
        processed_doc: dict = deepcopy(self.doc_expanded)
        self.ld_description = self._get_ld_description(processed_doc, drop=True)
        self.ld_about = self._get_ld_about(processed_doc, drop=True)
        self.ld_version = self._get_ld_version(processed_doc)
        self.ld_schema_version = self._get_ld_schema_version(processed_doc)
        self.ld_pref_label = self._get_ld_pref_label(processed_doc)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc)

    def export(self) -> InternalModel:
        return ActivityCreate(
            name=self.ld_pref_label or self.ld_alt_label,
            description=self.ld_description or {},
            image=self.ld_image,
            items=[],
        )


class ReproProtocol(LdDocumentBase, ContainsNestedMixin, CommonFieldsMixin):
    ld_shuffle: bool | None = None
    ld_allow: list[str] | None = None
    ld_order: list[str] | None = None
    ld_watermark: str | None = None
    extra: dict | None = None
    nested_by_order: list[LdDocumentBase] | None = None

    @classmethod
    def supports(cls, doc: dict) -> bool:
        ld_types = [
            'reproschema:Protocol',
            *cls.attr_processor.resolve_key('reproschema:Protocol')
        ]
        return doc.get(LdKeyword.type) in ld_types

    @classmethod
    def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
        return [ReproActivity]

    async def load(self, doc: dict, base_url: str | None = None):
        await super().load(doc, base_url)

        processed_doc = deepcopy(self.doc_expanded)
        self.ld_description = self._get_ld_description(processed_doc, drop=True)
        self.ld_about = self._get_ld_about(processed_doc, drop=True)
        self.ld_version = self._get_ld_version(processed_doc, drop=True)
        self.ld_schema_version = self._get_ld_schema_version(processed_doc, drop=True)
        self.ld_shuffle = self._get_ld_shuffle(processed_doc, drop=True)
        self.ld_allow = self._get_ld_allow(processed_doc)
        self.ld_pref_label = self._get_ld_pref_label(processed_doc)
        self.ld_alt_label = self._get_ld_alt_label(processed_doc)
        self.ld_image = self._get_ld_image(processed_doc, drop=True)
        self._get_ld_watermark(processed_doc, drop=True)
        await self._process_ld_order(processed_doc)

        self._load_extra(processed_doc)

    def _get_ld_watermark(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, 'reproschema:watermark', drop=drop)

    def _get_ld_shuffle(self, doc: dict, drop=False):
        return self.attr_processor.get_attr_value(doc, 'reproschema:shuffle', drop=drop)

    def _get_ld_allow(self, doc: dict, drop=False):
        key = self.attr_processor.get_key(doc, 'reproschema:allow')
        items = doc[key]
        if isinstance(items, list):
            return [item.get(LdKeyword.id) for item in items]
        if drop:
            del doc[key]

    async def _process_ld_order(self, doc: dict, drop=False):
        term_attr = 'reproschema:order'
        key = self.attr_processor.get_key(doc, term_attr)
        items = self.attr_processor.get_attr_single(doc, term_attr, ld_key=LdKeyword.list)
        self.ld_order = items

        nested = await asyncio.gather(*[self._load_nested(item) for item in items])
        self.nested_by_order = list(nested)

        if drop:
            del doc[key]

    async def _load_nested(self, doc: dict):
        return await self.load_supported_document(doc, self.base_url)

    def _load_extra(self, doc: dict):
        if self.extra is None:
            self.extra = {}
        for k, v in doc.items():
            self.extra[k] = v

    def export(self):
        activities = []
        activity_flows = []
        return AppletCreate(
            display_name=self.ld_pref_label or self.ld_alt_label,
            description=self.ld_description or {},
            about=self.ld_about or {},
            image=self.ld_image or '',
            watermark=self.ld_watermark or '',
            extra_fields=self.extra,
            activities=activities,
            activity_flows=activity_flows
        )
