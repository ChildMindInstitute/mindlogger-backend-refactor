import os

import psycopg2

from apps.shared.encryption import encrypt


class Postgres:
    def __init__(self) -> None:
        # Setup PostgreSQL connection
        self.connection = psycopg2.connect(
            host=os.getenv("DATABASE__HOST", "postgres"),
            port=os.getenv("DATABASE__PORT", "5432"),
            dbname=os.getenv("DATABASE__DB", "mindlogger_backend"),
            user=os.getenv("DATABASE__USER", "postgres"),
            password=os.getenv("DATABASE__PASSWORD", "postgres"),
        )

    def close_connection(self):
        self.connection.close()

    def encrypt_users(self) -> None:
        """Encrypt users fields: first_name and last_name"""
        cursor = self.connection.cursor()
        try:
            cursor.execute("SELECT id, first_name, last_name FROM users;")
            result = cursor.fetchall()
            for row in result:
                user_id, plain_first_name, plain_last_name = row
                if plain_first_name:
                    encrypted_first_name = encrypt(
                        bytes(plain_first_name, "utf-8")
                    ).hex()
                else:
                    encrypted_first_name = None
                if plain_last_name:
                    encrypted_last_name = encrypt(
                        bytes(plain_last_name, "utf-8")
                    ).hex()
                else:
                    encrypted_last_name = None
                cursor.execute(
                    "UPDATE users SET first_name = %s, last_name = %s "
                    "WHERE id = %s",
                    (encrypted_first_name, encrypted_last_name, user_id),
                )
        except Exception as e:
            print(f"Users encryption and updates generate error: {e}.")
        finally:
            self.connection.commit()
            cursor.close()

        print("Users encryption and updates completed.")

    def encrypt_users_workspaces(self) -> None:
        """Encrypt users_workspaces field: workspace_name"""
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "SELECT id, workspace_name FROM users_workspaces "
                "WHERE workspace_name IS NOT NULL;"
            )
            result = cursor.fetchall()
            for row in result:
                users_workspace_id, plain_workspace_name = row
                encrypted_workspace_name = encrypt(
                    bytes(plain_workspace_name, "utf-8")
                ).hex()
                cursor.execute(
                    "UPDATE users_workspaces SET workspace_name = %s "
                    "WHERE id = %s",
                    (encrypted_workspace_name, users_workspace_id),
                )
        except Exception as e:
            print(
                f"Users_workspaces encryption and updates generate error: {e}."
            )
        finally:
            self.connection.commit()
            cursor.close()

        print("Users_workspaces encryption and updates completed.")

    def encrypt_invitations(self) -> None:
        """Encrypt invitations fields: first_name and last_name"""
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "SELECT id, first_name, last_name FROM invitations;"
            )
            result = cursor.fetchall()
            for row in result:
                invitation_id, plain_first_name, plain_last_name = row
                if plain_first_name:
                    encrypted_first_name = encrypt(
                        bytes(plain_first_name, "utf-8")
                    ).hex()
                else:
                    encrypted_first_name = None
                if plain_last_name:
                    encrypted_last_name = encrypt(
                        bytes(plain_last_name, "utf-8")
                    ).hex()
                else:
                    encrypted_last_name = None
                cursor.execute(
                    "UPDATE invitations SET first_name = %s, last_name = %s "
                    "WHERE id = %s",
                    (encrypted_first_name, encrypted_last_name, invitation_id),
                )
        except Exception as e:
            print(f"Invitations encryption and updates generate error: {e}.")
        finally:
            self.connection.commit()
            cursor.close()

        print("Invitations encryption and updates completed.")

    def encrypt_answer_notes(self) -> None:
        """Encrypt answer_notes field: note"""
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "SELECT id, note FROM answer_notes WHERE note IS NOT NULL;"
            )
            result = cursor.fetchall()
            for row in result:
                answer_note_id, plain_note = row
                encrypted_note = encrypt(bytes(plain_note, "utf-8")).hex()
                cursor.execute(
                    "UPDATE answer_notes SET note = %s WHERE id = %s",
                    (encrypted_note, answer_note_id),
                )
        except Exception as e:
            print(f"Answer_notes encryption and updates generate error: {e}.")
        finally:
            self.connection.commit()
            cursor.close()

        print("Answer_notes encryption and updates completed.")

    def encrypt_alerts(self) -> None:
        """Encrypt alerts field: alert_message"""
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                "SELECT id, alert_message FROM alerts "
                "WHERE alert_message IS NOT NULL;"
            )
            result = cursor.fetchall()
            for row in result:
                alert_id, plain_alert_message = row
                encrypted_alert_message = encrypt(
                    bytes(plain_alert_message, "utf-8")
                ).hex()
                cursor.execute(
                    "UPDATE alerts SET alert_message = %s WHERE id = %s",
                    (encrypted_alert_message, alert_id),
                )
        except Exception as e:
            print(f"Alerts encryption and updates generate error: {e}.")
        finally:
            self.connection.commit()
            cursor.close()

        print("Alerts encryption and updates completed.")
