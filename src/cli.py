import os

abspath = os.path.abspath(__file__)
dname = os.path.dirname(os.path.dirname(abspath))
os.chdir(dname)


import typer  # noqa: E402

from apps.workspaces.commands import arbitrary_server_cli  # noqa: E402

cli = typer.Typer()
cli.add_typer(arbitrary_server_cli, name="arbitrary")


if __name__ == "__main__":
    # with app context?
    cli()
