from datetime import date, datetime

from bson import ObjectId
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from apps.alerts.db.schemas import AlertSchema
from apps.alerts.crud.alert import AlertCRUD

from apps.migrate.utilities import mongoid_to_uuid
from apps.migrate.services.mongo import decrypt

from infrastructure.database import atomic


__all__ = [
    "MongoAlert",
    "AlertMigrationService",
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


class MongoAlert(BaseModel):
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    accountId: PyObjectId = Field(default_factory=PyObjectId)
    alertMessage: bytes | str
    appletId: PyObjectId = Field(default_factory=PyObjectId)
    created: date
    itemId: PyObjectId = Field(default_factory=PyObjectId)
    itemSchema: str
    profileId: PyObjectId = Field(default_factory=PyObjectId)
    reviewerId: PyObjectId = Field(default_factory=PyObjectId)
    viewed: bool
    user_id: PyObjectId = Field(default_factory=PyObjectId)
    version: str


class AlertMigrationService:
    def __init__(self, session, alerts: list[MongoAlert]):
        self.session = session
        self.alerts = alerts

    async def run_alerts_migration(self):
        number_of_errors: int = 0
        number_of_alerts_in_mongo: int = len(self.alerts)
        for i, alert in enumerate(self.alerts, 1):
            print(
                f"Migrate alert {i}/{number_of_alerts_in_mongo}. Working on Alert: {alert.id}"
            )
            try:
                await self._create_alert(alert)
            except IntegrityError as e:
                number_of_errors += 1
                print(f"Skipped Alert: {alert.id}")
                # print(f"error is: {e}")
                continue
        print(f"Number of skiped alerts: {number_of_errors}")

    async def _create_alert(self, alert: MongoAlert):
        alert_data: dict = {}

        alert_data["user_id"] = mongoid_to_uuid(alert.reviewerId)
        alert_data["respondent_id"] = mongoid_to_uuid(alert.user_id)
        alert_data["is_watched"] = alert.viewed
        alert_data["applet_id"] = mongoid_to_uuid(alert.appletId)
        activity_id = alert.itemSchema.split("/")[0]
        alert_data["activity_id"] = mongoid_to_uuid(activity_id)
        alert_data["activity_item_id"] = mongoid_to_uuid(alert.itemId)
        alert_data["alert_message"] = decrypt(alert.alertMessage)
        alert_data["created_at"] = alert.created
        alert_data["version"] = alert.version
        alert_data["migrated_date"] = datetime.utcnow()

        alert = AlertSchema(**alert_data)

        async with atomic(self.session):
            await AlertCRUD(self.session)._create(alert)
