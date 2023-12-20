import argparse
import json
import uuid
import logging

from pydantic import BaseModel, validator

from apps.workspaces.domain.constants import Role
from bson import ObjectId


def mongoid_to_uuid(id_):
    if isinstance(id_, str) and "/" in id_:
        id_ = id_.split("/").pop()
    return uuid.UUID(str(id_) + "00000000")


def uuid_to_mongoid(uid: uuid.UUID | str) -> None | ObjectId:
    if isinstance(uid, str):
        uid = uuid.UUID(uid)
    return ObjectId(uid.hex[:-8]) if uid.hex[-8:] == "0" * 8 else None


def convert_role(role: str) -> str:
    match role:
        case "user":
            return Role.RESPONDENT
        case _:
            return role


logger_format = "%(asctime)s %(name)s %(levelname)s - %(message)s"
logger_format_date = "%Y-%m-%d %H:%M:%S"


def get_logger(name) -> logging.Logger:
    formatter = logging.Formatter(logger_format, logger_format_date)
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    # handler.setLevel(level=logging.ERROR)

    log = logging.getLogger(name)
    log.addHandler(handler)

    return log


def configure_report(logger, report_file: str | None = None):
    if report_file:
        report_handler = logging.FileHandler(report_file)
        report_handler.setFormatter(
            logging.Formatter(logger_format, logger_format_date)
        )
        report_handler.setLevel(logging.INFO)
        logger.addHandler(report_handler)


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


logging.basicConfig(
    level=logging.WARNING, format=logger_format, datefmt=logger_format_date
)
migration_log = get_logger("Migration")
migration_log.setLevel(logging.DEBUG)


class Params(BaseModel):
    class Config:
        orm_mode = True

    workspace: str | None = None
    applet: list[str] | None = None
    report_file: str | None = None

    @validator("applet", pre=True)
    def to_array(cls, value, values):
        if isinstance(value, str):
            return value.split(",")

        return value


def get_arguments() -> Params:
    parser = argparse.ArgumentParser()
    parser.add_argument("-w", "--workspace", type=str, required=False)
    parser.add_argument("-a", "--applet", type=str, required=False)
    parser.add_argument("-r", "--report_file", type=str, required=False)
    args = parser.parse_args()

    arguments = Params.from_orm(args)

    return arguments


def prepare_extra_fields_to_save(extra_fields: dict | None):
    if not extra_fields:
        return extra_fields
    for key in ("id", "created", "updated"):
        if key in extra_fields:
            extra_fields[key] = str(extra_fields[key])
    return extra_fields
