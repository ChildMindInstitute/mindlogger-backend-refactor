from apps.answers.crud import AnswerItemsCRUD
from apps.answers.db.schemas import AnswerItemSchema
from apps.girderformindlogger.models.item import Item
from apps.girderformindlogger.models.profile import Profile
from apps.migrate.answers.crud import MigrateUsersMCRUD

from apps.migrate.utilities import mongoid_to_uuid
from datetime import datetime


class AnswerItemMigrationService:
    async def create_item(
        self,
        *,
        regular_session,
        regular_or_arbitary_session,
        mongo_answer: dict,
        **kwargs,
    ):
        identifier = mongo_answer["meta"]["subject"].get("identifier", "")
        respondent_mongo_id = Profile().findOne(
            {"_id": mongo_answer["meta"]["subject"].get("@id")}
        )["userId"]
        if respondent_mongo_id:
            respondent_id = mongoid_to_uuid(respondent_mongo_id)
        else:
            anon_respondent = await MigrateUsersMCRUD(
                regular_session
            ).get_anonymous_respondent()
            respondent_id = anon_respondent.id

        answer_item = await AnswerItemsCRUD(
            regular_or_arbitary_session
        ).create(
            AnswerItemSchema(
                created_at=mongo_answer["created"],
                updated_at=mongo_answer["updated"],
                answer_id=kwargs["answer_id"],
                answer=mongo_answer["meta"]["dataSource"],
                item_ids=self._get_item_ids(mongo_answer),
                events=mongo_answer["meta"].get("events", ""),
                respondent_id=respondent_id,
                identifier=mongo_answer["meta"]["subject"].get(
                    "identifier", None
                ),
                user_public_key=str(mongo_answer["meta"]["userPublicKey"]),
                scheduled_datetime=self._fromtimestamp(
                    mongo_answer["meta"].get("scheduledTime")
                ),
                start_datetime=self._fromtimestamp(
                    mongo_answer["meta"].get("responseStarted")
                ),
                end_datetime=self._fromtimestamp(
                    mongo_answer["meta"].get("responseCompleted")
                ),
                is_assessment=kwargs["is_assessment"],
                migrated_date=datetime.utcnow(),
                migrated_data=self._get_migrated_data(identifier),
            )
        )
        return answer_item

    def _get_migrated_data(self, identifier):
        if not identifier:
            return None
        return {"is_identifier_encrypted": False}

    def _get_item_ids(self, mongo_answer):
        responses_keys = list(mongo_answer["meta"]["responses"])

        if not all([k.startswith("http") for k in responses_keys]):
            return [
                str(mongoid_to_uuid(k.split("/")[1]))
                for k in list(mongo_answer["meta"]["responses"])
            ]

        item_ids_from_url = [url.split("/")[-1] for url in responses_keys]
        return [
            str(mongoid_to_uuid(i["_id"]))
            for i in Item().find(
                query={
                    "meta.activityId": mongo_answer["meta"]["activity"]["@id"],
                    # If meta.screen.schema:url exists then try to find by url,
                    # because meta.screen.@id will start with '/'.
                    # In other case try to find by last word in url (screen.@id)
                    "$or": [
                        {"meta.screen.@id": {"$in": item_ids_from_url}},
                        {"meta.screen.schema:url": {"$in": responses_keys}},
                    ],
                }
            )
        ]

    def _fromtimestamp(self, timestamp: int | None):
        if timestamp is None:
            return None
        return datetime.utcfromtimestamp((float(timestamp) / 1000))
