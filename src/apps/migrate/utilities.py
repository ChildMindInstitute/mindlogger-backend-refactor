import argparse
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
migration_log.setLevel(logging.INFO)


def get_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--workspace", type=str, required=False)
    parser.add_argument("-a", "--applet", type=str, required=False)
    args = parser.parse_args()
    workspace = (
        args.workspace if "workspace" in args and args.workspace else None
    )
    applets = (
        args.applet.split(",") if "applet" in args and args.applet else None
    )
    if workspace and applets:
        raise Exception("Specify either workspace or applets arg")
    return workspace, applets
