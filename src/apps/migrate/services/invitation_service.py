import datetime
import uuid
from datetime import date

from bson import ObjectId
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.exc import IntegrityError

from apps.invitations.db.schemas import InvitationSchema
from apps.invitations.crud import InvitationCRUD
from apps.invitations.constants import InvitationStatus
from apps.workspaces.domain.constants import Role
from apps.migrate.services.mongo import decrypt


from apps.migrate.utilities import migration_log, mongoid_to_uuid

from infrastructure.database import atomic


__all__ = [
    "MongoInvitation",
    "InvitationsMigrationService",
]


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid objectid")
        return ObjectId(v)

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type="string")


class MongoInvitation(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    userEmail: EmailStr
    appletId: PyObjectId = Field(default_factory=PyObjectId)
    role: str
    inviterId: PyObjectId | None = Field(default_factory=PyObjectId)
    firstName: bytes | None
    lastName: bytes | None
    created: date
    updated: date


class InvitationsMigrationService:
    def __init__(self, session, invitations: list[MongoInvitation]):
        self.session = session
        self.invitations = invitations

    async def run_invitations_migration(self):
        number_of_errors: int = 0
        number_of_invitations_in_mongo: int = len(self.invitations)
        for i, invitation in enumerate(self.invitations, 1):
            migration_log.debug(
                f"Migrate invitation {i}/{number_of_invitations_in_mongo}. Working on Invitation: {invitation.id}"
            )
            if not invitation.inviterId:
                migration_log.debug(
                    f"Skipped Invitation: {invitation.id} (no invitation.inviterId)"
                )
                continue
            try:
                await self._create_invitation(invitation)
            except IntegrityError as e:
                number_of_errors += 1
                migration_log.debug(f"Skipped Invitation: {invitation.id} {e}")
                continue
        migration_log.info(f"Number of skiped invitations: {number_of_errors}")

    async def _create_invitation(self, invitation: MongoInvitation):
        invitation_data: dict = {}

        if invitation.userEmail:
            invitation_data["email"] = invitation.userEmail
        invitation_data["applet_id"] = mongoid_to_uuid(invitation.appletId)
        if invitation.role == "user":
            invitation_data["role"] = Role.RESPONDENT
        else:
            invitation_data["role"] = invitation.role
        invitation_data["invitor_id"] = mongoid_to_uuid(invitation.inviterId)
        invitation_data["status"] = InvitationStatus.PENDING
        if invitation.firstName:
            invitation_data["first_name"] = decrypt(invitation.firstName)
        if invitation.lastName:
            invitation_data["last_name"] = decrypt(invitation.lastName)
        invitation_data["created_at"] = invitation.created
        invitation_data["updated_at"] = invitation.updated
        invitation_data["key"] = uuid.uuid3(
            mongoid_to_uuid(invitation.id), invitation_data["email"]
        )
        invitation_data["meta"] = {}

        now = datetime.datetime.utcnow()
        invitation = InvitationSchema(
            **{
                **invitation_data,
                "migrated_date": now,
                "migrated_updated": now,
            }
        )

        async with atomic(self.session):
            await InvitationCRUD(self.session)._create(invitation)
