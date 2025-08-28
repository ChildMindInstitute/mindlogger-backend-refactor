import typer

from apps.activities.commands.delete_subscales import (
    delete_subscales_for_all_applet_versions as delete_subscales_fn,
)
from apps.activities.commands.reindex_items import app as reindex_app

app = typer.Typer(help="Activity CLI commands")
app.add_typer(reindex_app, name="reindex")
app.command()(delete_subscales_fn)

activities = app
__all__ = ["activities"]
