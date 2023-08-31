import asyncio
import traceback

from bson import ObjectId

from apps.answers.db.schemas import AnswerSchema
from apps.girderformindlogger.models.note import Note
from apps.girderformindlogger.models.profile import Profile
from apps.girderformindlogger.models.item import Item
from apps.migrate.answers.answer_item_service import AnswerItemMigrationService
from apps.migrate.answers.answer_note_service import AnswerNoteMigrateService
from apps.migrate.answers.answer_service import AnswerMigrationService
from apps.migrate.answers.crud import MigrateAnswersCRUD

from apps.migrate.services.mongo import Mongo
from apps.migrate.utilities import mongoid_to_uuid
from infrastructure.database import session_manager, atomic


class AnswersMigrateFacade:
    def __init__(self):
        self.mongo = Mongo()
        self.answer_migrate_service = AnswerMigrationService()
        self.answer_item_migrate_service = AnswerItemMigrationService()
        self.answer_note_migrate_service = AnswerNoteMigrateService()

    async def migrate(self):
        total_answers = 0
        successfully_answers_migrated = 0
        error_answers_migration = []
        skipped_answers_migration = 0
        answer_items_data = []

        session = session_manager.get_session()
        async with atomic(session):
            answers_migration_params = await MigrateAnswersCRUD(
                session
            ).get_answers_migration_params()

        for answer_migration_params in answers_migration_params:
            anwswers_with_files = self.mongo.get_answers_with_files(
                answer_migration_queries=self.mongo.get_answer_migration_queries(
                    **answer_migration_params
                )
            )
            for answer_with_files in anwswers_with_files:
                if not answer_with_files:
                    continue
                total_answers += 1
                try:
                    async with atomic(session):
                        query = answer_with_files["query"]
                        mongo_answer = answer_with_files["answer"]
                        files = answer_with_files.get("files", {})
                        mongo_answer_id = mongo_answer["_id"]

                        print(
                            f"Starting migration of answer with mongo id: {mongo_answer_id}"
                        )
                        is_assessment = "reviewing" in mongo_answer["meta"]

                        if not is_assessment:
                            if await self.answer_migrate_service.is_answer_migrated(
                                session=session,
                                answer_id=mongoid_to_uuid(mongo_answer["_id"]),
                            ):
                                continue
                            flow_history_id = await self.answer_migrate_service.get_flow_history_id(
                                session=session, response=mongo_answer
                            )
                            respondent_id = mongoid_to_uuid(
                                mongo_answer["creatorId"]
                            )
                            if not await self.answer_migrate_service.is_respondent_exist(
                                session=session, respondent_id=respondent_id
                            ):
                                skipped_answers_migration += 1
                                continue
                            answer: AnswerSchema = await self.answer_migrate_service.create_answer(
                                session=session,
                                mongo_answer=mongo_answer,
                                files=files,
                                flow_history_id=flow_history_id,
                                respondent_id=respondent_id,
                            )
                            answer_id = answer.id
                        else:
                            mongo_id = mongo_answer["meta"]["reviewing"][
                                "responseId"
                            ]
                            mongo_answer_assessment = Item().findOne(
                                query={"_id": mongo_id}
                            )
                            respondent_id = mongoid_to_uuid(
                                mongo_answer_assessment["creatorId"]
                            )
                            if not await self.answer_migrate_service.is_respondent_exist(
                                session=session, respondent_id=respondent_id
                            ):
                                skipped_answers_migration += 1
                                continue
                            answer_id = mongoid_to_uuid(mongo_id)

                        # Collect answer data to prevent integrity issues
                        answer_item_data = {
                            "mongo_answer": mongo_answer,
                            "answer_id": answer_id,
                            "is_assessment": is_assessment,
                        }

                        answer_items_data.append(answer_item_data)

                        for note in Note().find(
                            query={
                                "appletId": mongo_answer["meta"]["applet"][
                                    "@id"
                                ],
                                "responseId": mongo_answer["_id"],
                            }
                        ):
                            applet_profile = Profile().find(
                                query={"_id": note["userProfileId"]}
                            )[0]
                            await self.answer_note_migrate_service.create(
                                session=session,
                                note=note,
                                answer_id=answer_id,
                                applet_profile=applet_profile,
                            )
                    successfully_answers_migrated += 1
                except Exception as e:
                    error_answers_migration.append(
                        (query, f"mongo answer id {mongo_answer_id}", str(e))
                    )
                    continue

        for i, answer_item_data in enumerate(answer_items_data):
            print(f"Migrating {i} answer_item of {len(answer_items_data)}")
            try:
                async with atomic(session):
                    await self.answer_item_migrate_service.create_item(
                        session=session,
                        **answer_item_data,
                    )
            except Exception as e:
                error_answers_migration.append((answer_item_data, str(e)))
                continue

        print(f"Total answers count: {total_answers}")
        print(
            f"Successfully answers migrated count: {successfully_answers_migrated}"
        )
        print(f"Skipped answers migration count: {skipped_answers_migration}")
        print(f"Error answers migration count: {len(error_answers_migration)}")
        if error_answers_migration:
            print(
                f"Error asnwers migration data (mongo query, mongo item id, error):"
            )
            for s in error_answers_migration:
                print("#" * 10)
                print(s)

        self.mongo.close_connection()


if __name__ == "__main__":
    asyncio.run(AnswersMigrateFacade().migrate())
