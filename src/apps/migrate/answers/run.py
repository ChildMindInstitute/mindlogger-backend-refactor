import asyncio
import uuid
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
from apps.migrate.run import get_applets_ids

from apps.migrate.services.mongo import Mongo
from apps.migrate.utilities import (
    configure_report,
    migration_log,
    mongoid_to_uuid,
    get_arguments,
    intersection,
)
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from infrastructure.database import session_manager, atomic

from apps.activities.crud import (
    ActivityHistoriesCRUD,
    ActivityItemHistoriesCRUD,
)
from apps.activities.db.schemas import (
    ActivityHistorySchema,
    ActivityItemHistorySchema,
)


APPLETS_WITH_ISSUES_DONT_MIGRATE_ANSWERS = {
    "623cd7ee5197b9338bdaf218",
    "6116c49e66f506a576da4f03",
    "5fd28283c47c585b7c73354b",
    "5f0e35523477de8b4a528dd0",
    "61f3415f62485608c74c1f0b",
    "61f3423962485608c74c1f45",
    "623cb24d5197b9338bdaed65",
    "623ce1695197b9338bdaf388",
    "61f3419a62485608c74c1f25",
    "63d3d579b71996780cdf409a",
    "636533965cb70043112200a9",
    "636936b352ea02101467640d",
    "631aba1db7ee970ffa9009e3",
    "623ce52a5197b9338bdaf4b6",
    "623dfaf95197b9338bdaf8c5",
    "62f16366acd35a39e99b57ec",
    "636425cf5cb700431121fe46",
    "636532fd5cb700431121ff93",
    "636936ca52ea021014676437",
    "636936e652ea02101467645b",
    "636e942c52ea0234e1f4ec25",
}


class AnswersMigrateFacade:
    anonymous_respondent_answers = 0
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

    async def migrate(self, workspace, applets):
        regular_session = session_manager.get_session()

        applets_ids = await self._get_allowed_applets_ids(workspace, applets)
        applets_ids = [
            mongoid_to_uuid(applet_id)
            for applet_id in applets_ids
            if applet_id not in APPLETS_WITH_ISSUES_DONT_MIGRATE_ANSWERS
        ]

        await self._wipe_answers_data(regular_session, applets_ids)

        async for answer_with_files in self._collect_migratable_answers(
            applets_ids
        ):
            self.total_answers += 1
            query = answer_with_files["query"]
            mongo_answer = answer_with_files["answer"]
            files = answer_with_files.get("files", {})
            mongo_answer_id = mongo_answer["_id"]

            applet_id = mongoid_to_uuid(
                str(mongo_answer["meta"]["applet"]["@id"])
            )

            if applet_id not in applets_ids:
                continue

            try:
                regular_or_arbitary_session = (
                    await self._get_regular_or_arbitary_session(
                        regular_session, applet_id
                    )
                )
                async with atomic(regular_session):
                    async with atomic(regular_or_arbitary_session):
                        migration_log.info(
                            f"Starting migration of answer with mongo id: {mongo_answer_id}"
                        )
                        is_assessment = "reviewing" in mongo_answer["meta"]

                        if is_assessment:
                            answer_id = mongoid_to_uuid(
                                mongo_answer["meta"]["reviewing"]["responseId"]
                            )
                            await self._create_reviewer_assessment(
                                regular_session, mongo_answer
                            )

                        else:
                            if await self.answer_migrate_service.is_answer_migrated(
                                session=regular_or_arbitary_session,
                                answer_id=mongoid_to_uuid(mongo_answer["_id"]),
                            ):
                                continue
                            flow_history_id = await self.answer_migrate_service.get_flow_history_id(
                                session=regular_session,
                                response=mongo_answer,
                            )
                            respondent_mongo_id = Profile().findOne(
                                {
                                    "_id": mongo_answer["meta"]["subject"].get(
                                        "@id"
                                    )
                                }
                            )["userId"]

                            respondent_id = (
                                mongoid_to_uuid(respondent_mongo_id)
                                if respondent_mongo_id
                                else (
                                    await MigrateUsersMCRUD(
                                        regular_session
                                    ).get_anonymous_respondent()
                                ).id
                            )
                            if not respondent_mongo_id:
                                applet_owner = await UserAppletAccessCRUD(
                                    regular_session
                                ).get_applet_owner(applet_id)

                                await MigrateUserAppletAccessService(
                                    regular_session,
                                    applet_owner.user_id,
                                    applet_id,
                                ).add_role_for_anonymous_respondent()

                                self.anonymous_respondent_answers += 1

                            answer = await self.answer_migrate_service.create_answer(
                                session=regular_or_arbitary_session,
                                mongo_answer=mongo_answer,
                                files=files,
                                flow_history_id=flow_history_id,
                                respondent_id=respondent_id,
                            )
                            answer_id = answer.id

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

        async with atomic(regular_session):
            await self._migrate_answers_items(
                regular_session, self.answer_items_data
            )

        self._log_migration_results()

        self.mongo.close_connection()

    async def _wipe_answers_data(self, session, applets_ids):
        migration_log.info(f"Wiping responses of {len(applets_ids)} applet(s)")
        for applet_id in applets_ids:
            regular_or_arbitary_session = (
                await self._get_regular_or_arbitary_session(session, applet_id)
            )
            async with atomic(regular_or_arbitary_session):
                migrate_crud = AnswersMigrateCRUD(regular_or_arbitary_session)
                answers_ids = await migrate_crud.get_answers_ids(applet_id)
                for answer_id in answers_ids:
                    await migrate_crud.delete_answer(answer_id)

            async with atomic(session):
                migrate_crud = AnswersMigrateCRUD(session)
                for answer_id in answers_ids:
                    await migrate_crud.delete_note(answer_id)

    async def _get_allowed_applets_ids(self, workspace_id, applets_ids):
        allowed_applets_ids = await get_applets_ids()

        if workspace_id:
            applets_ids = intersection(
                self.mongo.get_applets_by_workspace(workspace_id),
                allowed_applets_ids,
            )
        elif not applets_ids:
            applets_ids = allowed_applets_ids

        return applets_ids

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

    async def _collect_migratable_answers(self, applets_ids: list[uuid.UUID]):
        migratable_data_count = 0

        regular_session = session_manager.get_session()

        async with atomic(regular_session):
            answers_migration_params = await AnswersMigrateCRUD(
                regular_session
            ).get_answers_migration_params(applets_ids)

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
            migration_log.debug(
                f"Migrating {i} answer_item of {len(answer_items_data)}"
            )
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
                        regular_session=regular_session,
                        regular_or_arbitary_session=regular_or_arbitary_session,
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
        migration_log.info(f"Total answers count: {self.total_answers}")
        migration_log.info(
            f"Successfully answers migrated count: {self.successfully_answers_migrated}"
        )
        migration_log.info(
            f"Skipped answers migration count: {self.skipped_answers_migration}"
        )
        migration_log.info(
            f"Error answers migration count: {len(self.error_answers_migration)}"
        )
        if self.error_answers_migration:
            migration_log.info(
                f"Error asnwers migration data (mongo query, mongo item id, error):"
            )
            for s in self.error_answers_migration:
                migration_log.info("#" * 10)
                migration_log.info(s)

        migration_log.info(
            f"Anonymous users answers count: {self.anonymous_respondent_answers}"
        )

    async def _create_reviewer_assessment(self, regular_session, mongo_answer):
        # check if reviewer assessment activity for this answers applet version exists
        original_answer = self.mongo.db["item"].find_one(
            {"_id": mongo_answer["meta"]["reviewing"]["responseId"]}
        )

        original_applet_id = mongoid_to_uuid(
            original_answer["meta"]["applet"]["@id"]
        )
        original_applet_version = original_answer["meta"]["applet"]["version"]

        all_assessment_activities = await ActivityHistoriesCRUD(
            regular_session
        ).retrieve_by_applet_ids(
            [
                f"{original_applet_id}_{original_applet_version}",
            ]
        )
        reviewer_assessment_activities = [
            _a for _a in all_assessment_activities if _a.is_reviewable
        ]
        if (
            len(all_assessment_activities) > 0
            and not reviewer_assessment_activities
        ):
            raise Exception(
                f"All activities are not reviewable, applet: {original_applet_id}, version: {original_applet_version}"
            )

        # if not, create it
        if not reviewer_assessment_activities:
            missing_applet_version = mongo_answer["meta"]["applet"]["version"]

            duplicating_activity_res = await ActivityHistoriesCRUD(
                regular_session
            ).get_reviewable_activities(
                [
                    f"{original_applet_id}_{missing_applet_version}",
                ]
            )
            if duplicating_activity_res:
                duplicating_activity = duplicating_activity_res[0]
                duplicating_activity_items = await ActivityItemHistoriesCRUD(
                    regular_session
                ).get_by_activity_id_version(duplicating_activity.id_version)
                duplicating_activity = dict(duplicating_activity)
                duplicating_activity[
                    "id_version"
                ] = f"{str(duplicating_activity['id'])}_{original_applet_version}"
                duplicating_activity[
                    "applet_id"
                ] = f"{str(original_applet_id)}_{original_applet_version}"
                duplicating_activity = await ActivityHistoriesCRUD(
                    regular_session
                )._create(ActivityHistorySchema(**duplicating_activity))
                for item in duplicating_activity_items:
                    item = dict(item)
                    item[
                        "id_version"
                    ] = f"{str(item['id'])}_{original_applet_version}"
                    item["activity_id"] = duplicating_activity.id_version
                    item = await ActivityItemHistoriesCRUD(
                        regular_session
                    )._create(ActivityItemHistorySchema(**item))


if __name__ == "__main__":
    args = get_arguments()
    configure_report(migration_log, args.report_file)
    asyncio.run(AnswersMigrateFacade().migrate(args.workspace, args.applet))
