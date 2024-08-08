import asyncio
import uuid

from rich import print
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.answers.db.schemas import AnswerItemSchema, AnswerSchema
from apps.answers.deps.preprocess_arbitrary import preprocess_arbitrary_url
from apps.applets.service import AppletService
from infrastructure.database import atomic, session_manager

# APPLET_ID = uuid.UUID("62be21d7-cd01-4b9b-975a-39750d940f59")
APPLET_ID = uuid.UUID("bfb5ca77-e43b-46fb-a702-4f6f667b4adc")  # for testing on uat
INSERT_BATCH_SIZE = 1000


def error_msg(msg: str):
    print(f"[bold red]Error: {msg}[/bold red]")


async def copy_answer_items(session: AsyncSession, arb_session: AsyncSession, applet_id: uuid.UUID):
    print("[green]Copy answer items...[/green]")

    query = (
        select(AnswerItemSchema.__table__)
        .join(AnswerSchema, AnswerSchema.id == AnswerItemSchema.answer_id)
        .where(AnswerSchema.applet_id == applet_id)
    )

    res = await session.execute(query)
    data = res.all()

    print(f"Total records in internal DB: {len(data)}")
    total_res = await arb_session.execute(query.with_only_columns(func.count(AnswerItemSchema.id)))
    total_arb = total_res.scalar()
    print(f"Total records in arbitrary DB: {total_arb}")

    for i in range(0, len(data), INSERT_BATCH_SIZE):
        values = [dict(row) for row in data[i : i + INSERT_BATCH_SIZE]]
        insert_query = (
            insert(AnswerItemSchema)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=[AnswerItemSchema.id],
            )
        )
        await arb_session.execute(insert_query)

    print("[green]Copy answer items - DONE[/green]")
    total_res = await arb_session.execute(query.with_only_columns(func.count(AnswerItemSchema.id)))
    total_arb = total_res.scalar()

    print(f"Total records in arbitrary DB: {total_arb}\n")


async def copy_answers(session: AsyncSession, arb_session: AsyncSession, applet_id: uuid.UUID):
    print("[green]Copy answers...[/green]")

    query = select(AnswerSchema.__table__).where(AnswerSchema.applet_id == applet_id)
    res = await session.execute(query)
    data = res.all()

    print(f"Total records in internal DB: {len(data)}")
    total_res = await arb_session.execute(query.with_only_columns(func.count(AnswerSchema.id)))
    total_arb = total_res.scalar()
    print(f"Total records in arbitrary DB: {total_arb}")

    for i in range(0, len(data), INSERT_BATCH_SIZE):
        values = [dict(row) for row in data[i : i + INSERT_BATCH_SIZE]]
        insert_query = (
            insert(AnswerSchema)
            .values(values)
            .on_conflict_do_nothing(
                index_elements=[AnswerSchema.id],
            )
        )
        await arb_session.execute(insert_query)

    print("[green]Copy answers - Done[/green]")

    total_res = await arb_session.execute(query.with_only_columns(func.count(AnswerSchema.id)))
    total_arb = total_res.scalar()

    print(f"Total records in arbitrary DB: {total_arb}")


async def main(
    session: AsyncSession,
    arbitrary_session: AsyncSession = None,
    *args,
    **kwargs,
):
    applet = await AppletService(session, uuid.uuid4()).get(APPLET_ID)
    arbitrary_uri = await preprocess_arbitrary_url(applet.id, session=session)
    if not arbitrary_uri:
        error_msg("Arbitrary db not set for the applet")
        return

    print(f"[green]Move answers for applet '{applet.display_name}'({applet.id})[/green]")

    session_maker = session_manager.get_session(arbitrary_uri)
    async with session_maker() as arb_session:
        try:
            print("Check DB availability...")
            await arb_session.execute("select current_date")
            print("[green]Database is available.[/green]")
        except asyncio.TimeoutError:
            error_msg("Timeout error")
            return
        except Exception as e:
            error_msg(str(e))
            return

        async with atomic(arb_session):
            await copy_answers(session, arb_session, applet.id)
        async with atomic(arb_session):
            await copy_answer_items(session, arb_session, applet.id)
