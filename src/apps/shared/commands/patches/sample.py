from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from apps.invitations.crud import InvitationCRUD
from apps.invitations.db.schemas import InvitationSchema


async def main(session: AsyncSession):
    await InvitationCRUD(session)._execute(
        update(InvitationSchema).values({"is_deleted": False})
    )
