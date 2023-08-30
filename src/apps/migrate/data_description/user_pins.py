import datetime
import uuid
from dataclasses import dataclass


@dataclass
class UserPinsDAO:
    user_id: uuid.UUID
    pinned_user_id: uuid.UUID
    owner_id: uuid.UUID
    role: str
    created_at: datetime.datetime
    updated_at: datetime.datetime

    def __hash__(self):
        return hash(
            (self.user_id, self.pinned_user_id, self.owner_id, self.role)
        )

    def __eq__(self, other):
        return hash(other) == hash(self)

    def __str__(self):
        values = (
            f"'{uuid.uuid4()}'::UUID",
            f"FALSE",
            f"'{self.user_id}'::UUID",
            f"'{self.pinned_user_id}'::UUID",
            f"'{self.owner_id}'::UUID",
            f"'{self.role}'",
            f"'{self.created_at}'::TIMESTAMP",
            f"'{self.updated_at}'::TIMESTAMP",
            f"'{datetime.datetime.now()}'::TIMESTAMP",
            f"'{datetime.datetime.now()}'::TIMESTAMP",
        )
        values = ",".join(values)
        return f"({values})"
