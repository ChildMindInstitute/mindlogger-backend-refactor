from datetime import datetime
from apps.answers.crud.notes import AnswerNotesCRUD
from apps.answers.db.schemas import AnswerNoteSchema
from apps.migrate.utilities import mongoid_to_uuid
from infrastructure.database import session_manager, atomic


class AnswerNoteMigrateService:
    async def create(self, *, session, note, answer_id, applet_profile):
        async with atomic(session):
            answer_note_schema = AnswerNoteSchema(
                id=mongoid_to_uuid(note["_id"]),
                created_at=note["created"],
                updated_at=note["updated"],
                answer_id=answer_id,
                note=note["note"],
                user_id=mongoid_to_uuid(applet_profile["userId"]),
                activity_id=mongoid_to_uuid(applet_profile["appletId"]),
                migrated_date=datetime.now(),
            )
            await AnswerNotesCRUD(session).save(answer_note_schema)
