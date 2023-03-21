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
)

from pyld.jsonld import JsonLdProcessor

from apps.applets.domain.applet_create import AppletCreate
from pyld import (
    ContextResolver,
    jsonld,
)

from apps.jsonld_converter.errors import JsonLDNotSupportedError
from apps.shared.domain import InternalModel

REPROSCHEMA_CONTEXT: str = "https://raw.githubusercontent.com/ReproNim/reproschema/master/contexts/generic"
CHILDMIND_CONTEXT: str = "https://raw.githubusercontent.com/ChildMindInstitute/reproschema-context/master/context.json"


class LdKeyword(str, enum.Enum):
    context = '@context'
    type = '@type'
    id = "@id"
    value = "@value"
    graph = "@graph"
    language = "@language"
    list = "@list"


class ContextResolverAwareMixin:
    document_loader: Callable = None
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


class LdDocumentBase(ABC, ContextResolverAwareMixin):
    base_url: str = None
    ld_ctx: list | dict | str = None
    doc: dict = None
    doc_expanded: dict = None
    lang = 'en'

    ld_id: str = None

    def __init__(self, context_resolver: ContextResolver, document_loader: Callable):
        self.context_resolver: ContextResolver = context_resolver
        self.document_loader = document_loader
        self.processor: JsonLdProcessor = JsonLdProcessor()

    @classmethod
    @abstractmethod
    def supports(cls, subject: dict) -> bool:
        ...

    @abstractmethod
    def export(self) -> InternalModel:
        ...

    async def load(self, doc: dict, base_url: str = None):
        self.doc = doc
        self.base_url = base_url
        self.ld_ctx = doc.get(LdKeyword.context)
        expanded = await self._expand(doc, base_url)
        self.doc_expanded = expanded[0]
        self.ld_id = self._get_first(self.doc_expanded, LdKeyword.id)

    async def _expand(self, doc: dict, base_url=None):
        options = dict(
            base=base_url,
            contextResolver=self.context_resolver,

        )
        return await asyncio.to_thread(jsonld.expand, doc, options)

    async def _load_context(self, active_ctx, ctx, base=None):
        if active_ctx is None:
            active_ctx = {'processingMode': 'json-ld-1.1', "mappings": {}}
        options = {
            'base': base,
            'documentLoader': self.document_loader,
            'contextResolver': self.context_resolver
        }
        return await asyncio.to_thread(self.processor.process_context, active_ctx, ctx, options)

    @classmethod
    def _get_first(cls, subject: dict, key: str):
        val = subject.get(key)
        if isinstance(val, list):
            return val[0]

        return val

    @classmethod
    def _get_lang_formatted(cls, items: list[dict]) -> dict:
        res = {}
        for item in items:
            lang, val = item.get(LdKeyword.language), item.get(LdKeyword.value)
            if lang:
                res[lang] = val
        return res

    def _get_attr_value(self, doc: dict, attr: str, ctx: dict, *, drop: bool = False):
        return self._get_attr(doc, attr, ctx, drop=drop, ld_key=LdKeyword.value)

    def _get_attr(self, doc: dict, attr: str, ctx: dict, *, drop: bool = False, ld_key: LdKeyword = None):
        key = self.processor.get_context_value(ctx, attr, LdKeyword.id)
        if key and key in doc:
            res = self._get_first(doc, key)
            if ld_key and res:
                res = res.get(ld_key)
            if drop and res is not None:
                del doc[key]

            return res

    def _get_translations(self, doc: dict, attr: str, ctx: dict, *, drop=False):
        key = self.processor.get_context_value(ctx, attr, LdKeyword.id)
        if key in doc:
            res = self._get_lang_formatted(doc[key])
            if drop:
                del doc[key]

            return res


class ReproActivity(LdDocumentBase, ContainsNestedMixin):

    @classmethod
    def supports(cls, subject: dict) -> bool:
        return subject.get(LdKeyword.type) in ['reproschema:Activity', 'http://schema.repronim.org/Activity']

    @classmethod
    def get_supported_types(cls) -> list[Type["LdDocumentBase"]]:
        return []

    async def load(self, doc: dict, base_url: str = None):
        await super().load(doc, base_url)

    def export(self) -> InternalModel:
        return None  # TODO


class ReproProtocol(LdDocumentBase, ContainsNestedMixin):
    ld_pref_label: str = None
    ld_alt_label: str = None
    ld_description: dict[str, str] = None
    ld_about: dict[str, str] = None
    ld_schema_version: str = None
    ld_version: str = None
    ld_shuffle: bool = None
    ld_allow: list = None
    ld_order: list[str] = None
    ld_image: str = None
    ld_watermark: str = None
    extra: dict = None

    @classmethod
    def supports(cls, subject: dict) -> bool:
        return subject.get(LdKeyword.type) in ['reproschema:Protocol', 'http://schema.repronim.org/Protocol']

    @classmethod
    def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
        return [ReproActivity]

    async def load(self, doc: dict, base_url: str = None):
        await super().load(doc, base_url)

        ctx = await self._load_context(None, CHILDMIND_CONTEXT, self.base_url)

        processed_doc = deepcopy(self.doc_expanded)
        self._pop_ld_description(processed_doc, ctx)
        self._pop_ld_about(processed_doc, ctx)
        self._pop_ld_version(processed_doc, ctx)
        self._pop_ld_schema_version(processed_doc, ctx)
        self._pop_ld_shuffle(processed_doc, ctx)
        self._pop_ld_allow(processed_doc, ctx)
        self._get_ld_pref_label(processed_doc, ctx)
        self._get_ld_alt_label(processed_doc, ctx)
        self._pop_ld_image(processed_doc, ctx)
        self._pop_ld_watermark(processed_doc, ctx)
        await self._pop_ld_order(processed_doc, ctx)

        self._load_extra(processed_doc)

    def _pop_ld_description(self, doc: dict, ctx: dict):
        self.ld_description = self._get_translations(doc, 'description', ctx, drop=True)

    def _pop_ld_about(self, doc: dict, ctx: dict):
        self.ld_about = self._get_translations(doc, 'about', ctx, drop=True)  # TODO what is the context???

    def _get_ld_pref_label(self, doc: dict, ctx: dict):
        items = self._get_translations(doc, 'prefLabel', ctx)
        if items:
            if val := items.get(self.lang):
                self.ld_pref_label = val
                return
            self.ld_pref_label = next(iter(items.values()))

    def _get_ld_alt_label(self, doc: dict, ctx: dict):
        items = self._get_translations(doc, 'altLabel', ctx)
        if items:
            if val := items.get(self.lang):
                self.ld_alt_label = val
                return
            self.ld_alt_label = next(iter(items.values()))

    def _pop_ld_version(self, doc: dict, ctx: dict):
        self.ld_version = self._get_attr_value(doc, 'version', ctx, drop=True)

    def _pop_ld_schema_version(self, doc: dict, ctx: dict):
        self.ld_schema_version = self._get_attr_value(doc, 'schemaVersion', ctx, drop=True)

    def _pop_ld_image(self, doc: dict, ctx: dict):
        img = self._get_attr(doc, 'image', ctx, drop=True, ld_key=LdKeyword.id)
        if not img:
            self._get_attr(doc, 'image', ctx, drop=True, ld_key=LdKeyword.value)
        self.ld_image = self._get_attr(doc, 'image', ctx, drop=True, ld_key=LdKeyword.id)

    def _pop_ld_watermark(self, doc: dict, ctx: dict):
        self.ld_watermark = self._get_attr_value(doc, 'watermark', ctx, drop=True)  # TODO what is the context???

    def _pop_ld_shuffle(self, doc: dict, ctx: dict):
        self.ld_shuffle = self._get_attr_value(doc, 'shuffle', ctx, drop=True)

    def _pop_ld_allow(self, doc: dict, ctx: dict):
        key = self.processor.get_context_value(ctx, 'allow', LdKeyword.id)
        if key in doc:
            items = doc.get(key)
            if isinstance(items, list):
                self.ld_allow = [item.get(LdKeyword.id) for item in items]
            del doc[key]

    async def _pop_ld_order(self, doc: dict, ctx: dict):
        key = self.processor.get_context_value(ctx, 'order', LdKeyword.id)
        if key in doc:
            items = self._get_first(doc, key)[LdKeyword.list]

            docs = await asyncio.gather(*[self._load_nested(item, ctx) for item in items])

            self.ld_order = docs
            del doc[key]

    async def _load_nested(self, doc: dict, ctx):
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
            description=self.ld_description,
            about=self.ld_about or '',
            image=self.ld_image or '',
            watermark=self.ld_watermark or '',
            extra_fields=self.extra,
            activities=activities,
            activity_flows=activity_flows
        )


class JsonLDModelConverter(ContainsNestedMixin):
    def __init__(self, context_resolver: ContextResolver, document_loader: Callable):
        self.context_resolver: ContextResolver = context_resolver
        self.document_loader: Callable = document_loader

    @classmethod
    def get_supported_types(cls) -> list[Type[LdDocumentBase]]:
        return [ReproProtocol, ReproActivity]

    async def convert(self, input_: str | dict,
                      base_url: str = None) -> InternalModel:
        obj = await self.load_supported_document(input_, base_url)

        return obj.export()
