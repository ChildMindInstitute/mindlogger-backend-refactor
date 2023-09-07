import os

import psycopg2

from apps.shared.encryption import decrypt, encrypt


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
        # Encryption and updates users: first_name
        cursor.execute(
            "SELECT id, first_name FROM users WHERE first_name IS NOT NULL;"
        )
        result = cursor.fetchall()
        count = 0
        for row in result:
            user_id, first_name = row
            if first_name:
                try:
                    decrypt(bytes.fromhex(first_name)).decode("utf-8")
                except ValueError:
                    encrypted_first_name = encrypt(
                        bytes(first_name, "utf-8")
                    ).hex()
                    cursor.execute(
                        "UPDATE users SET first_name = %s " "WHERE id = %s",
                        (encrypted_first_name, user_id),
                    )
                    count += 1
        self.connection.commit()
        print(
            "Users 'first_name' encryption and updates completed.\n"
            f"{count} - Updated Successfully!"
        )
        # Encryption and updates users: last_name
        cursor.execute(
            "SELECT id, last_name FROM users WHERE last_name IS NOT NULL;"
        )
        result = cursor.fetchall()
        count = 0
        for row in result:
            user_id, last_name = row
            if last_name:
                try:
                    decrypt(bytes.fromhex(last_name)).decode("utf-8")
                except ValueError:
                    encrypted_last_name = encrypt(
                        bytes(last_name, "utf-8")
                    ).hex()
                    cursor.execute(
                        "UPDATE users SET last_name = %s " "WHERE id = %s",
                        (encrypted_last_name, user_id),
                    )
                    count += 1
        self.connection.commit()
        print(
            "Users 'last_name' encryption and updates completed.\n"
            f"{count} - Updated Successfully!"
        )
        cursor.close()

    def encrypt_users_workspaces(self) -> None:
        """Encrypt users_workspaces field: workspace_name"""
        cursor = self.connection.cursor()
        # Encryption and updates users_workspaces: workspace_name
        cursor.execute(
            "SELECT id, workspace_name FROM users_workspaces "
            "WHERE workspace_name IS NOT NULL;"
        )
        result = cursor.fetchall()
        count = 0
        for row in result:
            users_workspace_id, workspace_name = row
            if workspace_name:
                try:
                    decrypt(bytes.fromhex(workspace_name)).decode("utf-8")
                except ValueError:
                    encrypted_workspace_name = encrypt(
                        bytes(workspace_name, "utf-8")
                    ).hex()
                    cursor.execute(
                        "UPDATE users_workspaces SET workspace_name = %s "
                        "WHERE id = %s",
                        (encrypted_workspace_name, users_workspace_id),
                    )
                    count += 1
        self.connection.commit()
        print(
            "Users_workspaces 'workspace_name' "
            "encryption and updates completed.\n"
            f"{count} - Updated Successfully!"
        )
        cursor.close()

    def encrypt_invitations(self) -> None:
        """Encrypt invitations fields: first_name and last_name"""
        cursor = self.connection.cursor()
        # Encryption and updates invitations: first_name
        cursor.execute(
            "SELECT id, first_name FROM invitations "
            "WHERE first_name IS NOT NULL;"
        )
        result = cursor.fetchall()
        count = 0
        for row in result:
            invitation_id, first_name = row
            if first_name:
                try:
                    decrypt(bytes.fromhex(first_name)).decode("utf-8")
                except ValueError:
                    encrypted_first_name = encrypt(
                        bytes(first_name, "utf-8")
                    ).hex()
                    cursor.execute(
                        "UPDATE invitations SET first_name = %s "
                        "WHERE id = %s",
                        (encrypted_first_name, invitation_id),
                    )
                    count += 1
        self.connection.commit()
        print(
            "Invitations 'first_name' encryption and updates completed.\n"
            f"{count} - Updated Successfully!"
        )
        # Encryption and updates invitations: last_name
        cursor.execute(
            "SELECT id, last_name FROM invitations "
            "WHERE last_name IS NOT NULL;"
        )
        result = cursor.fetchall()
        count = 0
        for row in result:
            invitation_id, last_name = row
            if last_name:
                try:
                    decrypt(bytes.fromhex(last_name)).decode("utf-8")
                except ValueError:
                    encrypted_last_name = encrypt(
                        bytes(last_name, "utf-8")
                    ).hex()
                    cursor.execute(
                        "UPDATE invitations SET last_name = %s "
                        "WHERE id = %s",
                        (encrypted_last_name, invitation_id),
                    )
                    count += 1
        self.connection.commit()
        print(
            "Invitations 'last_name' encryption and updates completed.\n"
            f"{count} - Updated Successfully!"
        )
        cursor.close()

    def encrypt_answer_notes(self) -> None:
        """Encrypt answer_notes field: note"""
        cursor = self.connection.cursor()
        # Encryption and updates answer_notes: note
        cursor.execute(
            "SELECT id, note FROM answer_notes WHERE note IS NOT NULL;"
        )
        result = cursor.fetchall()
        count = 0
        for row in result:
            answer_note_id, note = row
            if note:
                try:
                    decrypt(bytes.fromhex(note)).decode("utf-8")
                except ValueError:
                    encrypted_note = encrypt(bytes(note, "utf-8")).hex()
                    cursor.execute(
                        "UPDATE answer_notes SET note = %s " "WHERE id = %s",
                        (encrypted_note, answer_note_id),
                    )
                    count += 1
        self.connection.commit()
        print(
            "Answer_notes 'note' encryption and updates completed.\n"
            f"{count} - Updated Successfully!"
        )
        cursor.close()

    def encrypt_alerts(self) -> None:
        """Encrypt alerts field: alert_message"""
        cursor = self.connection.cursor()
        # Encryption and updates alerts: alert_message
        cursor.execute(
            "SELECT id, alert_message FROM alerts "
            "WHERE alert_message IS NOT NULL;"
        )
        result = cursor.fetchall()
        count = 0
        for row in result:
            alerts_id, alert_message = row
            if alert_message:
                try:
                    decrypt(bytes.fromhex(alert_message)).decode("utf-8")
                except ValueError:
                    encrypted_alert_message = encrypt(
                        bytes(alert_message, "utf-8")
                    ).hex()
                    cursor.execute(
                        "UPDATE alerts SET alert_message = %s "
                        "WHERE id = %s",
                        (encrypted_alert_message, alerts_id),
                    )
                    count += 1
        self.connection.commit()
        print(
            "Alerts 'alert_message' encryption and updates completed.\n"
            f"{count} - Updated Successfully!"
        )
        cursor.close()

    def re_encrypt_users_email_aes_encrypted(self) -> None:
        """transfer of encrypted data
        from field 'email_aes_encrypted' to field 'email_encrypted'
        """
        cursor = self.connection.cursor()
        cursor.execute(
            "SELECT id, email_aes_encrypted, email_encrypted FROM users "
            "WHERE email_aes_encrypted IS NOT NULL;"
        )
        result = cursor.fetchall()
        count = 0
        for row in result:
            user_id, email_aes_encrypted, email_encrypted_previous = row
            if email_aes_encrypted:
                try:
                    email = decrypt(email_aes_encrypted).decode("utf-8")
                except UnicodeDecodeError:
                    email = decrypt(
                        bytes.fromhex(
                            email_aes_encrypted.tobytes().decode("utf-8")
                        )
                    ).decode("utf-8")

                email_encrypted_current = encrypt(bytes(email, "utf-8")).hex()
                if email_encrypted_previous != email_encrypted_current:
                    cursor.execute(
                        "UPDATE users SET email_encrypted = %s "
                        "WHERE id = %s",
                        (email_encrypted_current, user_id),
                    )
                    count += 1
        self.connection.commit()
        print(
            "Users 'encrypted_email' encryption and updates completed.\n"
            f"{count} - Updated Successfully!"
        )
