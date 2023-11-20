import asyncio
from functools import wraps
from typing import Optional

import typer
from rich import print

from apps.answers.commands.crud import AssessmentCRUD
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
            session_maker = session_manager.get_session(database_uri)
        else:
            session_maker = session_manager.get_session()
        async with session_maker() as session:
            async with atomic(session):
                crud = AssessmentCRUD(session_maker)
                assessments = await crud.get_all_assessments_data()
                await crud.update_assessment(assessments)
    except Exception as ex:
        print(f"[bold red] {ex}")
