# NOTE: not used
import asyncio

from infrastructure.patch.migrate_to_encryptions.services.postgres import Postgres


async def main():
    """This is the procedure for encrypting fields in a database!
    It is designed to convert certain database fields into an encrypted form.
    And also for the correct transfer of encrypted data
    from field 'email_aes_encrypted' to field 'email_encrypted'
    """
    postgres = Postgres()

    postgres.encrypt_users()
    postgres.encrypt_users_workspaces()
    postgres.encrypt_invitations()
    postgres.encrypt_answer_notes()
    postgres.encrypt_alerts()

    postgres.re_encrypt_users_email_aes_encrypted()

    postgres.close_connection()


if __name__ == "__main__":
    asyncio.run(main())
