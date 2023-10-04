import datetime
import uuid
from dataclasses import dataclass
import json
from typing import Optional
from apps.migrate.utilities import EncUUID
from apps.workspaces.domain.constants import Role


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

    def dump_meta(self) -> str:
        if "legacyProfileId" in self.meta:
            self.meta["legacyProfileId"] = str(self.meta["legacyProfileId"])
        return json.dumps(self.meta, cls=EncUUID)

    def __hash__(self):
        return hash((self.user_id, self.applet_id, self.role))

    def __eq__(self, other):
        return hash(other) == hash(self)

    def insert_stmt(self) -> str:
        return """
            INSERT INTO user_applet_accesses
            (
                "id", 
                "migrated_date",
                "migrated_updated",
                "is_deleted", 
                "is_pinned",
                "role", 
                "user_id", 
                "applet_id",
                "owner_id",
                "invitor_id",
                "meta"
            )
            VALUES (
                %s,
                NOW(),
                NOW(),
                FALSE,
                %s, %s, %s, %s, %s, %s, %s
            )
        """

    def update_stmt(self):
        return """
        UPDATE user_applet_accesses 
            SET meta = jsonb_set(
                COALESCE(meta, '{}'::jsonb),
                '{legacyProfileId}',%s, true
            )
        WHERE 
            role = %s AND
            user_id = %s AND
            owner_id = %s AND
            applet_id = %s
        """

    def values(self) -> tuple:
        return (
            str(uuid.uuid4()),
            self.is_pinned,
            self.role,
            str(self.user_id),
            str(self.applet_id),
            str(self.owner_id),
            str(self.inviter_id),
            self.dump_meta(),
        )


def sort_by_role_priority(dao: AppletUserDAO):
    priority = {Role.OWNER.value: 0, Role.MANAGER.value: 1}
    return priority.get(dao.role, 3)
