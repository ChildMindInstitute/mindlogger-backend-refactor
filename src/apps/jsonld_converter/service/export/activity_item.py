from abc import abstractmethod

from apps.activities.domain.activity_full import (
    ActivityItemFull,
)
from apps.jsonld_converter.service.base import LdKeyword
from apps.jsonld_converter.service.export.base import (
    BaseModelExport,
)
from apps.shared.domain import (
    InternalModel,
    ResponseType,
)


class ActivityItemBaseExport(BaseModelExport):
    @classmethod
    def supports(cls, model: InternalModel) -> bool:
        return isinstance(model, ActivityItemFull)

    @classmethod
    @abstractmethod
    def _get_supported_response_type(cls) -> ResponseType:
        ...

    @abstractmethod
    def _get_input_type(self):
        ...

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = {
            LdKeyword.context: self.context,
            LdKeyword.id: f"_:{model.id}",
            LdKeyword.type: "reproschema:Field",
            "name": model.name,
            "skos:prefLabel": model.name,
            "skos:altLabel": model.name,
            "question": model.question,
            "ui": self._build_ui_prop(model)
        }
        response_options = self._build_response_options_prop(model)
        if response_options:
            doc["responseOptions"] = response_options

        return doc

    async def export(self, model: ActivityItemFull) -> dict:
        doc = self._build_doc(model)
        expanded = await self._expand(doc)

        return expanded[0]

    def _build_ui_prop(self, model: ActivityItemFull) -> dict:
        return {
            "inputType": self._get_input_type(),
            "allow": self._build_allow_prop(model)
        }

    def _build_allow_prop(self, model: ActivityItemFull) -> list[str]:
        allow = []
        if not model.config.remove_back_button:
            allow.append("disableBack")
        return allow

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        return None


class ActivityItemTextExport(ActivityItemBaseExport):
    @classmethod
    def _get_supported_response_type(cls) -> ResponseType:
        return ResponseType.TEXT

    def _get_input_type(self):
        return 'text'

    def _build_doc(self, model: ActivityItemFull) -> dict:
        doc = super()._build_doc(model)
        if model.config.correct_answer_required and (correct_answer := model.config.correct_answer):
            doc["correctAnswer"] = correct_answer
        doc.update({
            "correctAnswer": model.config.correct_answer
        })

        return doc

    def _build_allow_prop(self, model: ActivityItemFull) -> list[str]:
        allow = super()._build_allow_prop(model)
        if model.config.skippable_item:
            allow.append("dontKnow")
        return allow

    def _build_response_options_prop(self, model: ActivityItemFull) -> dict | None:
        value_type = "xsd:string"
        if model.config.numerical_response_required:
            value_type = "xsd:integer"
        options = {
            "valueType": value_type,
            "removeBackOption": model.config.remove_back_button,
            "requiredValue": model.config.response_required,
            "isResponseIdentifier": model.config.response_data_identifier,
            "maxLength": model.config.max_response_length
        }

        return options
