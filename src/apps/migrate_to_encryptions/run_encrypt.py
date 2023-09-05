import asyncio

from apps.migrate_to_encryptions.services.postgres import Postgres


async def main():
    """This procedure is for single use only!
    It is designed to convert certain database fields into an encrypted form.
    """
    postgres = Postgres()

    postgres.encrypt_users()
    postgres.encrypt_users_workspaces()
    postgres.encrypt_invitations()
    postgres.encrypt_answer_notes()
    postgres.encrypt_alerts()

    postgres.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
