import uuid
from datetime import datetime

from bson import ObjectId

from apps.answers.crud.answers import AnswersCRUD
from apps.answers.db.schemas import AnswerSchema
from apps.migrate.answers.crud import AnswersMigrateCRUD
from apps.migrate.utilities import mongoid_to_uuid
from apps.users import UsersCRUD


class AnswerMigrationService:
    async def is_answer_migrated(self, *, session, answer_id):
        try:
            await AnswersCRUD(session).get_by_id(answer_id)
            return True
        except Exception:
            return False

    async def is_respondent_exist(self, *, session, respondent_id):
        try:
            await UsersCRUD(session).get_by_id(respondent_id)
            return True
        except Exception:
            return False

    async def create_answer(
        self, *, session, mongo_answer, files, flow_history_id, respondent_id
    ):
        version = mongo_answer["meta"]["applet"]["version"]
        pk = self._generate_history_id(version)
        answer_schema = AnswerSchema(
            id=mongoid_to_uuid(mongo_answer["_id"]),
            created_at=mongo_answer["created"],
            updated_at=mongo_answer["updated"],
            applet_id=mongoid_to_uuid(
                str(mongo_answer["meta"]["applet"]["@id"])
            ),
            respondent_id=respondent_id,
            version=mongo_answer["meta"]["applet"]["version"],
            submit_id=self._get_submit_id(),
            applet_history_id=pk(
                mongoid_to_uuid(mongo_answer["meta"]["applet"]["@id"])
            ),
            flow_history_id=flow_history_id,
            activity_history_id=pk(
                mongoid_to_uuid(mongo_answer["meta"]["activity"]["@id"])
            ),
            client=mongo_answer["meta"]["client"],
            migrated_date=datetime.utcnow(),
            migrated_data=self._get_migrated_data(files),
        )
        answer = await AnswersCRUD(session).create(answer_schema)
        return answer

    def _get_direct_url(self, uri):
        return uri

    def _get_migrated_data(self, files):
        if not files:
            return None
        return {
            "decryptedFileAnswers": list(self._process_files(files)),
        }

    def _process_files(self, files):
        for item in files:
            key = next(iter(item))
            yield {
                "answerItemId": str(
                    mongoid_to_uuid(ObjectId(key.split("/").pop()))
                ),
                "fileUrl": self._get_direct_url(item[key]["value"]["uri"]),
            }

    def _generate_history_id(self, version: str):
        def key_generator(pk: uuid.UUID):
            return f"{pk}_{version}"

        return key_generator

    def _get_submit_id(self):
        return uuid.uuid4()

    async def get_flow_history_id(self, *, session, response):
        activity_flow = response["meta"].get("activityFlow")
        if not activity_flow:
            return None
        activity_flow_id = str(mongoid_to_uuid(activity_flow["@id"]))
        answer = await AnswersMigrateCRUD(session).get_flow_history_id_version(
            activity_flow_id
        )
        return answer
