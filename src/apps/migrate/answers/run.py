import asyncio

from apps.answers.db.schemas import AnswerSchema
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
    def __init__(self):
        self.mongo = Mongo()
        self.answer_migrate_service = AnswerMigrationService()
        self.answer_item_migrate_service = AnswerItemMigrationService()
        self.answer_note_migrate_service = AnswerNoteMigrateService()

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
            anwswers_with_files = self.mongo.get_answers_with_files(
                answer_migration_queries=self.mongo.get_answer_migration_queries(
                    **answer_migration_params
                )
            )
            for answer_with_files in anwswers_with_files:
                if not answer_with_files:
                    continue

                yield answer_with_files

                migratable_data_count += 1

                # if migratable_data_count >= 10000:
                #     return

    async def migrate(self):
        legacy_deleted_respondent_answers = 0
        total_answers = 0
        successfully_answers_migrated = 0
        error_answers_migration = []
        skipped_answers_migration = 0
        answer_items_data = []

        regular_session = session_manager.get_session()

        async for answer_with_files in self._collect_migratable_answers():
            total_answers += 1
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
                                mongo_answer["creatorId"]
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

                                applet_id = mongoid_to_uuid(
                                    str(mongo_answer["meta"]["applet"]["@id"])
                                )
                                applet_owner = await UserAppletAccessCRUD(
                                    regular_session
                                ).get_applet_owner(applet_id)

                                await MigrateUserAppletAccessService(
                                    regular_session,
                                    applet_owner.user_id,
                                    applet_id,
                                ).add_role_for_legacy_deleted_respondent()

                                legacy_deleted_respondent_answers += 1
                            answer: AnswerSchema = await self.answer_migrate_service.create_answer(
                                session=regular_or_arbitary_session,
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
                                session=regular_session,
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
                async with atomic(regular_session):
                    await self.answer_item_migrate_service.create_item(
                        session=regular_session,
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

        print(
            f"Legacy deleted users answers count: {legacy_deleted_respondent_answers}"
        )

        self.mongo.close_connection()


if __name__ == "__main__":
    asyncio.run(AnswersMigrateFacade().migrate())
