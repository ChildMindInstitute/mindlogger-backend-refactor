import uuid


class SeedError(Exception):
    """Base class for all seed-related exceptions."""

    def __init__(self, message: str):
        super().__init__(message)


class SeedUserIsDeletedError(SeedError):
    """Exception raised when trying to seed an applet using a deleted user."""

    def __init__(self, user_id_or_email: uuid.UUID | str):
        self.user_id_or_email = user_id_or_email
        super().__init__(f"User {user_id_or_email} is deleted.")


class SeedUserIdMismatchError(SeedError):
    """
    Exception raised when a seeded user has the same email address as an existing user in the database,
    but has a different user ID.
    """

    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id
        super().__init__(
            f"User ID mismatch. The user {user_id} already exists in the database by email address,"
            f" but has a different user ID"
        )


class EmailMismatchError(SeedError):
    """
    Exception raised when a seeded user already exists in the database, but the email in the existing user doesn't
    match the email in the seed file
    """

    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id
        super().__init__(
            f"User email mismatch. The user {user_id} already exists in the database with a different email address"
        )


class FirstNameMismatchError(SeedError):
    """
    Exception raised when a seeded user already exists in the database, but the first name in the existing user doesn't
    match the first name in the seed file
    """

    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id
        super().__init__(
            f"User first name mismatch. The user {user_id} already exists in the database with a different first name"
        )


class LastNameMismatchError(SeedError):
    """
    Exception raised when a seeded user already exists in the database, but the last name in the existing user doesn't
    match the last name in the seed file
    """

    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id
        super().__init__(
            f"User last name mismatch. The user {user_id} already exists in the database with a different last name"
        )


class PasswordMismatchError(SeedError):
    """
    Exception raised when a seeded user already exists in the database, but the password in the existing user doesn't
    match the password in the seed file
    """

    def __init__(self, user_id: uuid.UUID):
        self.user_id = user_id
        super().__init__(
            f"User password mismatch. The user {user_id} already exists in the database with a different password"
        )


class SubjectIdAlreadyExistsError(SeedError):
    """Exception raised when a seeded applet contains a subject with an ID that already exists in the database"""

    def __init__(self, subject_id: uuid.UUID, applet_id: uuid.UUID):
        self.subject_id = subject_id
        self.applet_id = applet_id
        super().__init__(f"Subject ID {subject_id} for applet {applet_id} already exists in the database.")


class EventIdAlreadyExistsError(SeedError):
    """
    Exception raised when a seeded applet contains one or more activities with an event ID that
    already exists in the database
    """

    def __init__(self, event_id: uuid.UUID, activity_id: uuid.UUID):
        self.event_id = event_id
        self.activity_id = activity_id
        super().__init__(f"Event ID {event_id} for activity {activity_id} already exists in the database.")


class AppletAlreadyExistsError(SeedError):
    """Exception raised when a seeded applet ID already exists in the database."""

    def __init__(self, applet_id: uuid.UUID):
        self.applet_id = applet_id
        super().__init__(f"Applet {applet_id} already exists in the database.")


class AppletNameAlreadyExistsError(SeedError):
    """Exception raised when a seeded applet name already exists in the database."""

    def __init__(self, applet_name: str):
        self.applet_name = applet_name
        super().__init__(f"The applet name {applet_name} already exists in the database.")


class AppletActivityIdsAlreadyExistsError(SeedError):
    """Exception raised when a seeded applet already has activities in the database."""

    def __init__(self, applet_id: uuid.UUID):
        self.applet_id = applet_id
        super().__init__(
            f"One or more of the activity/flow IDs in the applet {applet_id} already exist in the database."
        )


class AppletOwnerNotFoundError(SeedError):
    """Exception raised when a seeded applet has an owner that does not exist in the database."""

    def __init__(self, applet_id: uuid.UUID, user_id: uuid.UUID):
        self.user_id = user_id
        self.applet_id = applet_id
        super().__init__(f"Unexpected Error: Owner {user_id} of applet {applet_id} was not found in the database.")


class AppletWithoutOwnerError(SeedError):
    """Exception raised when a seeded applet does not have an owner"""

    def __init__(self, applet_id: uuid.UUID):
        self.applet_id = applet_id
        super().__init__(f"Unexpected Error: Applet {applet_id} does not have an owner")


class AppletOwnerWithoutUserIdError(SeedError):
    """Exception raised when a seeded applet has an owner without a user ID"""

    def __init__(self, applet_id: uuid.UUID):
        self.applet_id = applet_id
        super().__init__(f"Unexpected Error: Applet {applet_id} owner does not have a user ID")
