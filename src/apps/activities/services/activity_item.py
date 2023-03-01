import uuid

from apps.activities.crud import ActivityItemsCRUD
from apps.activities.domain.activity_item import ActivityItemDetail


class ActivityItemService:
    async def get_single_language_by_activity_id(
        self, activity_id: uuid.UUID, language: str
    ) -> list[ActivityItemDetail]:
        schemas = await ActivityItemsCRUD().get_by_activity_id(activity_id)
        items = []
        for schema in schemas:
            items.append(
                ActivityItemDetail(
                    id=schema.id,
                    activity_id=schema.activity_id,
                    question=self._get_by_language(schema.question, language),
                    response_type=schema.response_type,
                    # TODO: get answers by language
                    answers=schema.answers,
                    color_palette=schema.color_palette,
                    timer=schema.timer,
                    has_token_value=schema.has_token_value,
                    is_skippable=schema.is_skippable,
                    has_alert=schema.has_alert,
                    has_score=schema.has_score,
                    is_random=schema.is_random,
                    is_able_to_move_to_previous=(
                        schema.is_able_to_move_to_previous
                    ),
                    has_text_response=schema.has_text_response,
                    ordering=schema.ordering,
                )
            )
        return items

    @staticmethod
    def _get_by_language(values: dict, language: str):
        """
        Returns value by language key,
         if it does not exist,
         returns first existing or empty string
        """
        try:
            return values[language]
        except KeyError:
            for key, val in values.items():
                return val
            return ""
