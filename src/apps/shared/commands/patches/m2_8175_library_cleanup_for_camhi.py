from rich import print
from sqlalchemy.ext.asyncio import AsyncSession

# Dictionary mapping applet_id_version prefixes to expected names
EXPECTED_APPLETS = {
    "39847772-6cb3-4779-a353-af33c9afbe57": "CAMHI Behavioral Parental Therapy (Greek)",
    "9768accc-5e3a-4f47-96d3-57e932d2263a": "CAMHI Depression Therapy (Greek)",
    "3d9c6e8a-05a8-445c-90ff-6870b583b1bf": "CAMHI Anxiety Therapy (Greek)",
    "dc2cb5c9-e742-48f2-87ac-4fba469cdb1a": "CAMHI Behavior Parent Therapy - Therapist Review (Greek)",
    "cbdbd82b-14e0-47ef-b5ec-328539474925": "CAMHI Anxiety Therapy - Therapist Self Review (Greek)",
    "1dd5273b-639b-4933-b301-598106bf1cd3": "CAMHI Depression Therapy - Therapist Self Review (Greek Version)",
    "91bd8a50-3102-4a77-ad14-910c71c0a27a": "CAMHI Behavioral Parent Therapy - Supervisor's Review",
    "1b6d3ec1-b9f9-4a69-835f-b2b18606fc35": "CAMHI Depression Therapy - Supervisor's Review",
    # The extra space at the end of this applet's name is intentional
    "a94a7f9c-4657-451e-b67f-29ce6bf51603": "CAMHI Anxiety Therapy - Supervisor's Review ",
}

SQL_SELECT_LIBRARIES = """
    SELECT applet_id_version, applet_histories.display_name
    FROM library
    JOIN applet_histories ON library.applet_id_version = applet_histories.id_version
    WHERE applet_id_version LIKE ANY (ARRAY[{}]);
"""

SQL_DELETE_LIBRARIES = """
    DELETE FROM library
    WHERE applet_id_version LIKE ANY (ARRAY[{}]);
"""


async def main(session: AsyncSession, *args, **kwargs):
    # Start transaction
    async with session.begin():
        try:
            # Create the LIKE patterns for the SQL query
            patterns = ["'" + prefix + "_%'" for prefix in EXPECTED_APPLETS.keys()]
            pattern_list = ", ".join(patterns)

            # Execute SELECT query
            print("Executing SELECT query:")
            result = await session.execute(SQL_SELECT_LIBRARIES.format(pattern_list))
            rows = result.fetchall()

            # Validate results
            print(f"Found {len(rows)} rows")
            print("Validating results...")
            for row in rows:
                applet_id_version, display_name = row
                # Find matching prefix
                matching_prefix = next(
                    (prefix for prefix in EXPECTED_APPLETS.keys() if applet_id_version.startswith(prefix)), None
                )
                if not matching_prefix:
                    raise ValueError(f"No matching prefix found for {applet_id_version}")

                expected_name = EXPECTED_APPLETS[matching_prefix]
                if display_name != expected_name:
                    raise ValueError(
                        f"Name mismatch for {applet_id_version}: expected '{expected_name}', got '{display_name}'"
                    )

            # If validation passed, execute DELETE
            print("Validation passed. Executing DELETE query:")
            await session.execute(SQL_DELETE_LIBRARIES.format(pattern_list))
            print("Delete successful")

        except Exception as e:
            print(f"Error occurred: {str(e)}")
            print("Rolling back transaction...")
            raise  # This will trigger rollback

    print("Transaction committed successfully")
