"""CLI commands for MFA management and account recovery."""

import datetime
import uuid
from typing import Annotated

import typer
from rich import print
from sqlalchemy import select

from apps.authentication.db.schemas import RecoveryCodeSchema
from apps.users import UserIsDeletedError, UserNotFound, UsersCRUD
from infrastructure.commands.utils import coro
from infrastructure.database import atomic, session_manager
from infrastructure.logger import logger
from infrastructure.utility.redis_client import RedisCache

app = typer.Typer(short_help="Manage user MFA settings")


@app.command(short_help="Clear MFA for a user")
@coro
async def clear(
    user_identifier: Annotated[str, typer.Argument(help="User UUID or email")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip confirmation")] = False,
):
    s_maker = session_manager.get_session()
    async with s_maker() as session:
        async with atomic(session):
            users_crud = UsersCRUD(session)

            try:
                user_id = uuid.UUID(user_identifier)
                user = await users_crud.get_by_id(user_id)
            except ValueError:
                user = await users_crud.get_by_email(user_identifier)
                if not user:
                    print(f"Error: User with email {user_identifier} not found")
                    raise typer.Exit(code=1)
                user_id = user.id
            except (UserNotFound, UserIsDeletedError):
                print("Error: User does not exist or is deleted")
                raise typer.Exit(code=1)

            if not user.mfa_enabled:
                print(f"MFA is not enabled for user {user_id}")
                raise typer.Exit(code=0)

            print(f"Found user {user_id}")
            print(f"  Email: {user.email_encrypted}")
            print(f"  MFA Enabled: {user.mfa_enabled}")

            recovery_codes_query = select(RecoveryCodeSchema).where(RecoveryCodeSchema.user_id == user_id)
            recovery_codes_result = await session.execute(recovery_codes_query)
            recovery_codes = recovery_codes_result.scalars().all()
            recovery_code_count = len(recovery_codes)
            print(f"  Recovery Codes: {recovery_code_count}")

            if not yes:
                print(f"\nThis will disable MFA for user {user_id}")
                typer.confirm("Are you sure you want to proceed?", abort=True)

            redis_client = RedisCache()
            lockout_key = f"mfa_fail:{user_id}"
            lockout_cleared = await redis_client.delete(lockout_key)

            disabled_at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
            await users_crud.disable_mfa(user_id=user_id, disabled_at=disabled_at)

            logger.info(
                f"MFA disabled for user {user_id}",
                extra={
                    "user_id": str(user_id),
                    "disabled_at": disabled_at.isoformat(),
                    "recovery_codes_deleted": recovery_code_count,
                    "redis_lockout_cleared": lockout_cleared,
                },
            )

            print("\nMFA successfully disabled")
            print(f"  Disabled at: {disabled_at.isoformat()}")
            print(f"  Recovery codes deleted: {recovery_code_count}")
            print(f"  Redis lockout cleared: {'Yes' if lockout_cleared else 'No'}")


@app.command(short_help="Check MFA status for a user")
@coro
async def status(
    user_identifier: Annotated[str, typer.Argument(help="User UUID or email")],
):
    s_maker = session_manager.get_session()
    async with s_maker() as session:
        users_crud = UsersCRUD(session)

        try:
            user_id = uuid.UUID(user_identifier)
            user = await users_crud.get_by_id(user_id)
        except ValueError:
            user = await users_crud.get_by_email(user_identifier)
            if not user:
                print(f"Error: User with email {user_identifier} not found")
                raise typer.Exit(code=1)
            user_id = user.id
        except (UserNotFound, UserIsDeletedError):
            print("Error: User does not exist or is deleted")
            raise typer.Exit(code=1)

        recovery_codes_query = select(RecoveryCodeSchema).where(RecoveryCodeSchema.user_id == user_id)
        recovery_codes_result = await session.execute(recovery_codes_query)
        recovery_codes = recovery_codes_result.scalars().all()
        unused_count = sum(1 for code in recovery_codes if not code.used_at)

        print(f"\nMFA Status for User {user_id}\n")
        print(f"  Email: {user.email_encrypted}")
        print(f"  Name: {user.first_name} {user.last_name}")
        print(f"  MFA Enabled: {'Yes' if user.mfa_enabled else 'No'}")
        print(f"  MFA Secret Set: {'Yes' if user.mfa_secret else 'No'}")
        print(f"  Pending Setup: {'Yes' if user.pending_mfa_secret else 'No'}")
        print(f"  Recovery Codes: {unused_count} unused / {len(recovery_codes)} total")

        if user.mfa_disabled_at:
            print(f"  Last Disabled: {user.mfa_disabled_at.isoformat()}")

        print()


@app.callback()
def callback():
    pass
