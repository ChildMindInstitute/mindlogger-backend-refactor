import asyncio
from typing import Any

from bson import ObjectId

from apps.answers.deps.preprocess_arbitrary import (
    get_arbitrary_info,
)
from apps.girderformindlogger.models.note import Note
from apps.girderformindlogger.models.profile import Profile
from apps.migrate.answers.answer_item_service import AnswerItemMigrationService
from apps.migrate.answers.answer_note_service import AnswerNoteMigrateService
from apps.migrate.answers.answer_service import AnswerMigrationService
from apps.migrate.answers.crud import AnswersMigrateCRUD, MigrateUsersMCRUD
from apps.migrate.answers.user_applet_access import (
    MigrateUserAppletAccessService,
)
from apps.migrate.answers.user_service import UserMigrateService

from apps.migrate.services.mongo import Mongo
from apps.migrate.utilities import mongoid_to_uuid
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from infrastructure.database import session_manager, atomic


class AnswersMigrateFacade:
    legacy_deleted_respondent_answers = 0
    total_answers = 0
    successfully_answers_migrated = 0
    error_answers_migration: list[Any] = []
    skipped_answers_migration = 0
    answer_items_data: list[Any] = []

    def __init__(self):
        self.mongo = Mongo()
        self.answer_migrate_service = AnswerMigrationService()
        self.answer_item_migrate_service = AnswerItemMigrationService()
        self.answer_note_migrate_service = AnswerNoteMigrateService()

    async def migrate(self):
        regular_session = session_manager.get_session()

        async for answer_with_files in self._collect_migratable_answers():
            self.total_answers += 1
            query = answer_with_files["query"]
            mongo_answer = answer_with_files["answer"]
            files = answer_with_files.get("files", {})
            mongo_answer_id = mongo_answer["_id"]

            applet_id = mongoid_to_uuid(
                str(mongo_answer["meta"]["applet"]["@id"])
            )

            try:
                regular_or_arbitary_session = (
                    await self._get_regular_or_arbitary_session(
                        regular_session, applet_id
                    )
                )
                async with atomic(regular_session):
                    async with atomic(regular_or_arbitary_session):
                        print(
                            f"Starting migration of answer with mongo id: {mongo_answer_id}"
                        )
                        is_assessment = "reviewing" in mongo_answer["meta"]

                        if not is_assessment:
                            if await self.answer_migrate_service.is_answer_migrated(
                                session=regular_or_arbitary_session,
                                answer_id=mongoid_to_uuid(mongo_answer["_id"]),
                            ):
                                continue
                            flow_history_id = await self.answer_migrate_service.get_flow_history_id(
                                session=regular_session,
                                response=mongo_answer,
                            )
                            respondent_id = mongoid_to_uuid(
                                mongo_answer["meta"]["subject"].get("@id")
                            )
                            if not await self.answer_migrate_service.is_respondent_exist(
                                session=regular_session,
                                respondent_id=respondent_id,
                            ):
                                legacy_deleted_respondent = (
                                    await MigrateUsersMCRUD(
                                        regular_session
                                    ).get_legacy_deleted_respondent()
                                )
                                respondent_id = legacy_deleted_respondent.id

                                applet_owner = await UserAppletAccessCRUD(
                                    regular_session
                                ).get_applet_owner(applet_id)

                                await MigrateUserAppletAccessService(
                                    regular_session,
                                    applet_owner.user_id,
                                    applet_id,
                                ).add_role_for_legacy_deleted_respondent()

                                self.legacy_deleted_respondent_answers += 1
                            answer = await self.answer_migrate_service.create_answer(
                                session=regular_or_arbitary_session,
                                mongo_answer=mongo_answer,
                                files=files,
                                flow_history_id=flow_history_id,
                                respondent_id=respondent_id,
                            )
                            answer_id = answer.id
                        else:
                            answer_id = mongoid_to_uuid(
                                mongo_answer["meta"]["reviewing"]["responseId"]
                            )

                        answer_item_data = {
                            "mongo_answer": mongo_answer,
                            "answer_id": answer_id,
                            "is_assessment": is_assessment,
                            "applet_id": applet_id,
                        }

                        # Collect answer data to prevent integrity issues
                        data_source = mongo_answer["meta"].get("dataSource")
                        if not data_source:
                            continue
                        self.answer_items_data.append(answer_item_data)

                        await self._migrate_answers_notes(
                            mongo_answer, regular_session, answer_id
                        )

                self.successfully_answers_migrated += 1
            except Exception as e:
                self.error_answers_migration.append(
                    (query, f"mongo answer id {mongo_answer_id}", str(e))
                )
                continue

        await self._migrate_answers_items(
            regular_session, self.answer_items_data
        )

        self._log_migration_results()

        self.mongo.close_connection()

    async def _get_regular_or_arbitary_session(self, session, applet_id):
        arbitrary_url = await get_arbitrary_info(applet_id, session)
        arbitary_session = (
            session_manager.get_session(arbitrary_url)
            if arbitrary_url
            else None
        )
        if arbitary_session:
            return arbitary_session
        return session

    async def _collect_migratable_answers(self):
        migratable_data_count = 0

        regular_session = session_manager.get_session()

        await UserMigrateService(
            regular_session
        ).create_legacy_deleted_respondent()

        async with atomic(regular_session):
            answers_migration_params = await AnswersMigrateCRUD(
                regular_session
            ).get_answers_migration_params()

        for answer_migration_params in answers_migration_params:
            answer_migration_queries = self.mongo.get_answer_migration_queries(
                **answer_migration_params
            )
            anwswers_with_files = self.mongo.get_answers_with_files(
                answer_migration_queries=answer_migration_queries
            )
            for answer_with_files in anwswers_with_files:
                if not answer_with_files:
                    continue

                yield answer_with_files

                migratable_data_count += 1

    async def _migrate_answers_items(self, regular_session, answer_items_data):
        for i, answer_item_data in enumerate(answer_items_data):
            print(f"Migrating {i} answer_item of {len(answer_items_data)}")
            applet_id = answer_item_data["applet_id"]
            original_answer_id = answer_item_data["mongo_answer"]["_id"]

            # Test accounts problem answers
            if original_answer_id in [
                ObjectId("62fa4f85924264104c28edfe"),
                ObjectId("62fa4f43924264104c28edfc"),
                ObjectId("642190d583718f0fbf0b38c5"),
                ObjectId("642287c583718f0fbf0b424b"),
            ]:
                continue

            regular_or_arbitary_session = (
                await self._get_regular_or_arbitary_session(
                    regular_session, applet_id
                )
            )
            try:
                async with atomic(regular_or_arbitary_session):
                    await self.answer_item_migrate_service.create_item(
                        session=regular_session,
                        **answer_item_data,
                    )
            except Exception as e:
                self.error_answers_migration.append((answer_item_data, str(e)))
                continue

    async def _migrate_answers_notes(
        self, mongo_answer, regular_session, answer_id
    ):
        for note in Note().find(
            query={
                "appletId": mongo_answer["meta"]["applet"]["@id"],
                "responseId": mongo_answer["_id"],
            }
        ):
            applet_profile = Profile().find(
                query={"_id": note["userProfileId"]}
            )[0]
            await self.answer_note_migrate_service.create(
                session=regular_session,
                note=note,
                answer_id=answer_id,
                applet_profile=applet_profile,
            )

    def _log_migration_results(self):
        print(f"Total answers count: {self.total_answers}")
        print(
            f"Successfully answers migrated count: {self.successfully_answers_migrated}"
        )
        print(
            f"Skipped answers migration count: {self.skipped_answers_migration}"
        )
        print(
            f"Error answers migration count: {len(self.error_answers_migration)}"
        )
        if self.error_answers_migration:
            print(
                f"Error asnwers migration data (mongo query, mongo item id, error):"
            )
            for s in self.error_answers_migration:
                print("#" * 10)
                print(s)

        print(
            f"Legacy deleted users answers count: {self.legacy_deleted_respondent_answers}"
        )


if __name__ == "__main__":
    asyncio.run(AnswersMigrateFacade().migrate())
