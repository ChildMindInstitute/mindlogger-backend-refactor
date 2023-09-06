import datetime
import uuid
from dataclasses import dataclass
import json
from typing import Optional
from apps.migrate.utilities import EncUUID


@dataclass
class AppletUserDAO:
    applet_id: uuid.UUID
    user_id: uuid.UUID
    owner_id: uuid.UUID
    inviter_id: Optional[uuid.UUID]
    role: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
    meta: dict
    is_pinned: bool
    is_deleted: bool

    def __hash__(self):
        return hash((self.user_id, self.applet_id, self.role))

    def __eq__(self, other):
        return hash(other) == hash(self)

    def __str__(self):
        values = (
            f"'{uuid.uuid4()}'::UUID",
            f"'{self.created_at}'::TIMESTAMP",
            f"'{self.updated_at}'::TIMESTAMP",
            str(self.is_deleted),
            f"'{self.role}'",
            f"'{self.user_id}'::UUID",
            f"'{self.applet_id}'::UUID",
            f"'{self.owner_id}'::UUID",
            (f"'{self.inviter_id}'::UUID" if self.inviter_id else "NULL"),
            f"'{json.dumps(self.meta, cls=EncUUID)}'",
            str(self.is_pinned),
            f"'{datetime.datetime.utcnow()}'::TIMESTAMP",
            f"'{datetime.datetime.utcnow()}'::TIMESTAMP",
        )
        return f"({','.join(values)})"
