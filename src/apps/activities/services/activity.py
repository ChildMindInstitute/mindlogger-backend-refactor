import uuid

from apps.activities.crud import ActivitiesCRUD
from apps.activities.domain.activity import (
    ActivityDetail,
    ActivityExtendedDetail,
)
from apps.activities.services.activity_item import ActivityItemService


class ActivityService:
    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id

    async def get_single_language_by_applet_id(
        self, applet_id: uuid.UUID, language: str
    ) -> list[ActivityDetail]:
        schemas = await ActivitiesCRUD().get_by_applet_id(applet_id)
        activities = []
        for schema in schemas:
            activities.append(
                ActivityDetail(
                    id=schema.id,
                    name=schema.name,
                    description=self._get_by_language(
                        schema.description, language
                    ),
                    splash_screen=schema.splash_screen,
                    image=schema.image,
                    show_all_at_once=schema.show_all_at_once,
                    is_skippable=schema.is_skippable,
                    is_reviewable=schema.is_reviewable,
                    response_is_editable=schema.response_is_editable,
                    ordering=schema.ordering,
                )
            )
        return activities

    async def get_single_language_by_id(
        self, id_: uuid.UUID, language: str
    ) -> ActivityExtendedDetail:
        schema = await ActivitiesCRUD().get_by_id(self.user_id, id_)
        activity = ActivityExtendedDetail(
            id=schema.id,
            name=schema.name,
            description=self._get_by_language(schema.description, language),
            splash_screen=schema.splash_screen,
            image=schema.image,
            show_all_at_once=schema.show_all_at_once,
            is_skippable=schema.is_skippable,
            is_reviewable=schema.is_reviewable,
            response_is_editable=schema.response_is_editable,
            ordering=schema.ordering,
        )
        activity.items = (
            await ActivityItemService().get_single_language_by_activity_id(
                id_, language
            )
        )
        return activity

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
