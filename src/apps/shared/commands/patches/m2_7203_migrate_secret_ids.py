import datetime
import os
import uuid

from bson import ObjectId
from pymongo import MongoClient
from rich import print
from rich.style import Style
from rich.table import Table
from sqlalchemy import Text, column, select, update
from sqlalchemy.cimmutabledict import immutabledict
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Values

from apps.subjects.db.schemas import SubjectSchema

MARKER_DELETED = "#deleted#"
UPDATED_AT = datetime.datetime.utcnow().date()


def mongoid_to_uuid(id_):
    if isinstance(id_, str) and "/" in id_:
        id_ = id_.split("/").pop()
    return uuid.UUID(str(id_) + "00000000")


def uuid_to_mongoid(uid: uuid.UUID | str) -> None | ObjectId:
    if isinstance(uid, str):
        uid = uuid.UUID(uid)
    return ObjectId(uid.hex[:-8]) if uid.hex[-8:] == "0" * 8 else None


class MongoService:
    def __init__(self, uri: str, port: int, db_name: str):
        self.client: MongoClient = MongoClient(uri, port)
        self.db = self.client[db_name]

    @classmethod
    def from_env(cls):
        uri = os.getenv("MONGO_URI")
        port = os.getenv("MONGO_PORT", 27017)
        db_name = os.getenv("MONGO_DB")
        if not uri or not db_name:
            raise Exception("Env MONGO_URI, MONGO_DB required")

        return cls(uri, port, db_name)

    def get_applet_empty_roles(self, applet_id):
        collection = self.db["appletProfile"]
        profiles = collection.find(
            {"appletId": applet_id, "roles": {"$exists": True, "$size": 0}, "MRN": {"$exists": True}}
        )

        return list(profiles)


async def get_applet_ids(session: AsyncSession):
    query = select(SubjectSchema.applet_id).where(SubjectSchema.secret_user_id == MARKER_DELETED).distinct()
    res = await session.execute(query)
    data = res.scalars().all()

    return data


async def update_roles_from_subjects(session: AsyncSession):
    query = f"""
        update user_applet_accesses uaa
        set
            meta = jsonb_set(meta, '{{secretUserId}}', to_jsonb(s.secret_user_id)),
            updated_at = '{UPDATED_AT}',
            migrated_updated = '{UPDATED_AT}'
        from subjects s 
        where 1 = 1
            and uaa.applet_id = s.applet_id
            and uaa.user_id  = s.user_id 
            and uaa.role = 'respondent'
            and uaa.meta->>'secretUserId' = '{MARKER_DELETED}'
            and s.secret_user_id != '{MARKER_DELETED}'
    """
    res = await session.execute(query)

    return res.rowcount


async def migrate_subjects(applet_id, profiles, session: AsyncSession):
    data = [(mongoid_to_uuid(row["userId"]), row["MRN"]) for row in profiles if isinstance(row["MRN"], str)]
    if not data:
        print("[bold red]No valid data to migrate[/bold red]")
        return 0

    vals = Values(
        column("user_id", UUID(as_uuid=True)),
        column("secret_user_id", Text),
        name="profile_data",
    ).data(data)

    query = (
        update(SubjectSchema)
        .where(
            SubjectSchema.applet_id == applet_id,
            SubjectSchema.user_id == vals.c.user_id,
            SubjectSchema.secret_user_id == MARKER_DELETED,
        )
        .values(secret_user_id=vals.c.secret_user_id, updated_at=UPDATED_AT, migrated_updated=UPDATED_AT)
    ).returning(SubjectSchema.id, SubjectSchema.applet_id, SubjectSchema.user_id)

    res = await session.execute(query, execution_options=immutabledict({"synchronize_session": False}))
    migrated_data = res.all()

    table = Table(
        "Applet ID",
        "User ID",
        "Subject ID",
        show_header=True,
        title=f"Migrated subjects for {applet_id}",
        title_style=Style(bold=True),
    )
    for row in migrated_data:
        table.add_row(str(row.applet_id), str(row.user_id), str(row.id))
    print(table)

    return len(migrated_data)


async def main(
    session: AsyncSession,
    arbitrary_session: AsyncSession = None,
    *args,
    **kwargs,
):
    applet_ids = await get_applet_ids(session)
    total = 0
    if applet_ids:
        service = MongoService.from_env()
        for applet_id in applet_ids:
            print(f"[green]Applet {applet_id} migration start[/green]")
            roles = service.get_applet_empty_roles(uuid_to_mongoid(applet_id))
            if not roles:
                print(f"No roles for {applet_id} found. Skipping...")
                continue
            cnt = await migrate_subjects(applet_id, roles, session)
            print(f"[green]Applet {applet_id}: migrated {cnt} records[/green]")

            total += cnt

        roles_cnt = await update_roles_from_subjects(session)
        if total != roles_cnt:
            raise Exception(f"Migrated subjects: {total}, migrated roles: {roles_cnt}")

    print(f"[green]Migrated total: {total}[/green]")
