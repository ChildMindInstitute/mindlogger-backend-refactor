import os

abspath = os.path.abspath(__file__)
dname = os.path.dirname(os.path.dirname(abspath))
os.chdir(dname)


import typer  # noqa: E402, I001

from apps.activities.commands import activities  # noqa: E402
from apps.answers.commands import convert_assessments  # noqa: E402
from apps.applets.commands import ( # noqa: E402
    applet_cli,  # noqa: E402
    applet_ema_cli,  # noqa: E402
)
from apps.shared.commands import encryption_cli, patch  # noqa: E402
from apps.users.commands import token_cli  # noqa: E402
from apps.workspaces.commands import arbitrary_server_cli  # noqa: E402

cli = typer.Typer()
cli.add_typer(arbitrary_server_cli, name="arbitrary")
cli.add_typer(convert_assessments, name="assessments")
cli.add_typer(activities, name="activities")
cli.add_typer(token_cli, name="token")
cli.add_typer(patch, name="patch")
cli.add_typer(encryption_cli, name="encryption")
cli.add_typer(applet_ema_cli, name="applet-ema")
cli.add_typer(applet_cli, name="applet")

if __name__ == "__main__":
    # with app context?
    cli()
