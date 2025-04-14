from typing import Dict

from rich import print
from sqlalchemy.ext.asyncio import AsyncSession


async def main(session: AsyncSession, applets: Dict[str, str] | None = None, *args, **kwargs):
    """
    Cleanup libraries for CAMHI applets.
    """
    if applets:
        applet_id_prefixes = list(applets.keys())

        # Format the prefixes for the SQL query
        formatted_prefixes = [prefix + "%" for prefix in applet_id_prefixes]

        # Construct the SQL query
        sql_select = """
            SELECT applet_id_version, applet_histories.display_name
            FROM library
            JOIN applet_histories ON library.applet_id_version = applet_histories.id_version
            WHERE applet_id_version LIKE ANY (ARRAY[{}]);
        """.format(", ".join([f"'{prefix}'" for prefix in formatted_prefixes]))

        sql_delete = """
            DELETE FROM library
            WHERE applet_id_version LIKE ANY (ARRAY[{}]);
        """.format(", ".join([f"'{prefix}'" for prefix in formatted_prefixes]))

        # Start transaction
        async with session.begin():
            try:
                # Execute the SQL query
                result = await session.execute(sql_select)
                entries = result.fetchall()

                # Validate results
                print(f"Found {len(entries)} rows")

                if len(entries) == 0:
                    raise ValueError("No rows found to delete.")

                print("Validating results...")
                for entry in entries:
                    applet_id_version, display_name = entry
                    # Find matching prefix
                    matching_prefix = next(
                        (prefix for prefix in applets.keys() if applet_id_version.startswith(prefix)), None
                    )
                    if not matching_prefix:
                        raise ValueError(f"No matching prefix found for {applet_id_version}")

                    expected_name = applets[matching_prefix]
                    if display_name != expected_name:
                        raise ValueError(
                            f"Name mismatch for {applet_id_version}: expected '{expected_name}', got '{display_name}'"
                        )

                # If validation passed, execute DELETE
                print("Validation passed. Executing DELETE query:")
                await session.execute(sql_delete)
                print("Delete successful")

            except Exception as e:
                print(f"Error occurred: {str(e)}")
                print("Rolling back transaction...")
                raise  # This will trigger rollback

        print("Transaction committed successfully")
    else:
        print(
            "[bold red]No applets provided. Please provide applet ID-name map as JSON string to --applets option.[/bold red]"  # noqa: E501
        )
        return
