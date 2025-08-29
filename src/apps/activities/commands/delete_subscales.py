from uuid import UUID

import typer
from sqlalchemy import text

from infrastructure.commands.utils import coro
from infrastructure.database import session_manager

app = typer.Typer(help="Delete subscales and score-type reports across all versions of an applet.")

DROP_SCORE_FUNC_SQL = """
CREATE OR REPLACE FUNCTION drop_score_reports(sr jsonb)
RETURNS jsonb LANGUAGE sql IMMUTABLE AS $$
  SELECT CASE
    WHEN sr ? 'reports' THEN
      jsonb_set(
        sr, '{reports}',
        COALESCE(
          (SELECT jsonb_agg(r)
           FROM jsonb_array_elements(sr->'reports') r
           WHERE r->>'type' <> 'score'),
          '[]'::jsonb
        ),
        true
      )
    ELSE sr
  END;
$$;
"""


@app.command(name="delete-subscales-for-all-applet-versions")
@coro
async def delete_subscales_for_all_applet_versions(
    applet_id: UUID = typer.Argument(..., help="Base applet ID (UUID)"),
) -> None:
    """
    Remove all subscales and score-type reports from every version of the specified applet.
    """
    # obtain a session maker; then call it to get an async session
    s_maker = session_manager.get_session()
    async with s_maker() as session:
        await session.execute(text(DROP_SCORE_FUNC_SQL))
        await session.commit()

        # Get the list of version IDs for this applet
        versions_sql = text("""
            SELECT id_version
            FROM applet_histories
            WHERE id = :applet_id
        """)
        versions = (
            (
                await session.execute(
                    versions_sql,
                    {"applet_id": applet_id},
                )
            )
            .scalars()
            .all()
        )

        if not versions:
            typer.echo(f"No history versions found for applet {applet_id}.")
            return

        # Delete subscales and score-type reports in both tables
        hist_update_sql = text("""
            UPDATE activity_histories
            SET subscale_setting = NULL,
                scores_and_reports = CASE
                    WHEN scores_and_reports IS NULL THEN NULL
                    ELSE drop_score_reports(scores_and_reports)
                END
            WHERE applet_id = ANY(:versions)
        """)
        live_update_sql = text("""
            UPDATE activities
            SET subscale_setting = NULL,
                scores_and_reports = CASE
                    WHEN scores_and_reports IS NULL THEN NULL
                    ELSE drop_score_reports(scores_and_reports)
                END
            WHERE applet_id = :applet_id
        """)

        await session.execute(hist_update_sql, {"versions": versions})
        await session.execute(live_update_sql, {"applet_id": applet_id})
        await session.commit()

        typer.echo(f"Deleted subscales and score-type reports for {len(versions)} version(s) of applet {applet_id}.")
