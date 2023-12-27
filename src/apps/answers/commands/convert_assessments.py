import asyncio
from functools import wraps
from typing import Optional

import typer
from rich import print

from apps.answers.crud.assessment_crud import AssessmentCRUD
from infrastructure.database import atomic, session_manager

app = typer.Typer()


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper


@app.command(short_help="Convert current assessments to version agnostic")
@coro
async def convert(
    database_uri: Optional[str] = typer.Option(
        None,
        "--db-uri",
        "-d",
        help="Local or arbitrary server database uri",
    ),
):
    try:
        if database_uri:
            local_or_arb = session_manager.get_session(database_uri)
        else:
            local_or_arb = session_manager.get_session()
        # Going to arbitrary or local db to get assessments
        async with local_or_arb() as session:
            crud = AssessmentCRUD(session)
            assessments = await crud.get_all_assessments_data()

        # Going to local db to find activity id
        local = session_manager.get_session()
        async with local() as session:
            async with atomic(session):
                crud = AssessmentCRUD(session)
                answers = await crud.get_updated_assessment(assessments)
        await local.remove()

        # Return to arbitrary or local to update
        async with local_or_arb() as session:
            async with atomic(session):
                crud = AssessmentCRUD(session)
                for answer in answers:
                    await crud.update(answer)
        await local_or_arb.remove()

    except Exception as ex:
        print(f"[bold red] {ex}")
