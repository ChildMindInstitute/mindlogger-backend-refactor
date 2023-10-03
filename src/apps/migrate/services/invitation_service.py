from datetime import date

from bson import ObjectId
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from apps.invitations.db.schemas import InvitationSchema
from apps.invitations.crud import InvitationCRUD
from apps.invitations.constants import InvitationStatus


from apps.migrate.utilities import mongoid_to_uuid

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
    userEmail: str | None
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
            print(
                f"Migrate invitation {i}/{number_of_invitations_in_mongo}. Working on Invitation: {invitation.id}"
            )
            if not invitation.inviterId:
                print(f"Skipped Invitation: {invitation.id}")
                continue
            try:
                await self._create_invitation(invitation)
            except IntegrityError as e:
                number_of_errors += 1
                print(f"Skipped Invitation: {invitation.id}")
                continue
        print(f"Number of skiped invitations: {number_of_errors}")

    async def _create_invitation(self, invitation: MongoInvitation):
        invitation_data: dict = {}

        if invitation.userEmail:
            invitation_data["email"] = invitation.userEmail
        invitation_data["applet_id"] = mongoid_to_uuid(invitation.appletId)
        invitation_data["role"] = invitation.role
        invitation_data["invitor_id"] = mongoid_to_uuid(invitation.inviterId)
        invitation_data["status"] = InvitationStatus.PENDING
        if invitation.firstName:
            invitation_data["first_name"] = invitation.firstName
        if invitation.lastName:
            invitation_data["last_name"] = invitation.lastName
        invitation_data["created_at"] = invitation.created
        invitation_data["updated_at"] = invitation.updated

        invitation = InvitationSchema(**invitation_data)

        async with atomic(self.session):
            await InvitationCRUD(self.session)._create(invitation)
