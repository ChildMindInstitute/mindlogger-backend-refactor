import asyncio
import os
import uuid

from rich import print
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Query

from apps.answers.db.schemas import AnswerSchema
from apps.workspaces.crud.user_applet_access import UserAppletAccessCRUD
from apps.workspaces.db.schemas import UserAppletAccessSchema
from apps.workspaces.domain.constants import Role
from apps.workspaces.service.workspace import WorkspaceService
from infrastructure.database import session_manager

LOCAL_DB_PATCH_SQL = """
    insert into user_applet_accesses (
        id,
        is_deleted, 
        "role", 
        user_id, 
        applet_id, 
        owner_id, 
        invitor_id, 
        meta,
        created_at,
        updated_at,
        migrated_date 
    )
    select
        gen_random_uuid(),
        true,
        'respondent',
        answers.respondent_id,
        a.id,
        owner.user_id,
        owner.user_id,
        '{"secretUserId": "#deleted#"}'::jsonb,
        now() AT TIME ZONE 'UTC',
        now() AT TIME ZONE 'UTC',
        max(answers.migrated_date)
    from applets a 
    join user_applet_accesses owner on owner.applet_id = a.id and role = 'owner'
    join answers on answers.applet_id = a.id
    left join user_applet_accesses uaa 
        on uaa.applet_id = answers.applet_id and uaa.user_id = answers.respondent_id and uaa."role" = 'respondent'
    where 1=1
        and uaa.id is null
    group by a.id, answers.respondent_id, owner.user_id
"""


async def get_answer_count(session: AsyncSession):
    query: Query = select(func.count(AnswerSchema.id))
    db_result = await session.execute(query)
    return db_result.first()[0]


async def get_answers_applets_respondents(
    session: AsyncSession, limit: int, offset: int
) -> set[tuple[uuid.UUID, uuid.UUID]]:
    query: Query = select(AnswerSchema.respondent_id, AnswerSchema.applet_id)
    query = query.distinct(AnswerSchema.respondent_id, AnswerSchema.applet_id)
    query = query.limit(limit)
    query = query.offset(offset)
    query = query.order_by(AnswerSchema.respondent_id.asc(), AnswerSchema.applet_id.asc())
    db_result = await session.execute(query)
    answer_applet_resp = db_result.all()
    return {(a.respondent_id, a.applet_id) for a in answer_applet_resp}


async def get_missing_applet_respondent(
    session: AsyncSession, applet_ids: list[uuid.UUID], arbitrary_applet_respondents: set[tuple[uuid.UUID, uuid.UUID]]
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    query: Query = select(UserAppletAccessSchema.user_id, UserAppletAccessSchema.applet_id)
    query = query.where(
        UserAppletAccessSchema.applet_id.in_(applet_ids), UserAppletAccessSchema.role == Role.RESPONDENT
    )
    db_result = await session.execute(query)
    roles_users_applets = db_result.all()
    return list(arbitrary_applet_respondents - set(roles_users_applets))


async def find_and_create_missing_roles_arbitrary(
    session: AsyncSession, arbitrary_session: AsyncSession, owner_id: uuid.UUID
):
    count = await get_answer_count(arbitrary_session)
    if not count:
        print(f"Workspace: {owner_id}", f"answers count: {count}", "skip")
        return

    limit = int(os.environ.get("M2_6879_BATCH_SIZE", "1000"))
    total_missing = 0
    roles = []
    for offset in range(0, count, limit):
        arbitrary_applet_respondents = await get_answers_applets_respondents(arbitrary_session, limit, offset)

        applet_ids = {x[1] for x in arbitrary_applet_respondents}

        missing_users_applets = await get_missing_applet_respondent(
            session, list(applet_ids), arbitrary_applet_respondents
        )
        for user_id, applet_id in missing_users_applets:
            schema = UserAppletAccessSchema(
                user_id=user_id,
                applet_id=applet_id,
                role=Role.RESPONDENT,
                owner_id=owner_id,
                invitor_id=owner_id,
                meta={"secretUserId": "#deleted#"},
                is_deleted=True,
            )
            roles.append(schema)
            total_missing += len(missing_users_applets)

    await UserAppletAccessCRUD(session).create_many(roles)
    print(
        f"Workspace: {owner_id}",
        f"answers count: {count}",
        f"missing_roles: {total_missing}",
        "done",
    )


async def main(session: AsyncSession, *args, **kwargs):
    try:
        await session.execute(LOCAL_DB_PATCH_SQL)
        await session.commit()

        workspaces = await WorkspaceService(session, uuid.uuid4()).get_arbitrary_list()
        print(f"Found {len(workspaces)} workspaces with arbitrary servers")

        processed = set()
        for i, workspace in enumerate(workspaces):
            if arb_uri := workspace.database_uri:
                print(f"Processing workspace#{i + 1} {workspace.id}")
                if arb_uri in processed:
                    print(f"Workspace#{i + 1} DB already processed, skip...")
                    continue
                processed.add(arb_uri)
                try:
                    session_maker = session_manager.get_session(arb_uri)
                    async with session_maker() as arb_session:
                        try:
                            await find_and_create_missing_roles_arbitrary(session, arb_session, workspace.user_id)
                            await session.commit()
                            print(f"Processing workspace#{i + 1} {workspace.id} " f"finished")
                        except Exception:
                            await session.rollback()
                            print(f"[bold red]Error: Workspace#{i + 1} {workspace.id} processing error[/bold red]")
                            raise
                except asyncio.TimeoutError:
                    print(f"[bold red]Error: Workspace#{i + 1} {workspace.id} Timeout error, skipping...[/bold red]")
    except Exception as ex:
        await session.rollback()
        raise ex
