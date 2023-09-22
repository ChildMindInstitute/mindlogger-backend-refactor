import json
import sys
import uuid
import logging
from apps.workspaces.domain.constants import Role
from bson import ObjectId


def mongoid_to_uuid(id_):
    if isinstance(id_, str) and "/" in id_:
        id_ = id_.split("/").pop()
    return uuid.UUID(str(id_) + "00000000")


def uuid_to_mongoid(uid: uuid.UUID) -> None | ObjectId:
    return ObjectId(uid.hex[:-8]) if uid.hex[-8:] == "0" * 8 else None


def convert_role(role: str) -> str:
    match role:
        case "user":
            return Role.RESPONDENT
        case _:
            return role


def get_logger(name) -> logging.Logger:
    formatter = logging.Formatter(f"[{name}] %(levelname)s - %(message)s")
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(formatter)
    log = logging.getLogger()
    log.addHandler(handler)
    return log

def intersection(lst1, lst2):
    # Use of hybrid method
    temp = set(lst2)
    lst3 = [value for value in lst1 if value in temp]
    return lst3


class EncUUID(json.JSONEncoder):
    def default(self, t):
        if isinstance(t, uuid.UUID):
            return str(t)
        return super().default(t)


migration_log = get_logger("Migration")
