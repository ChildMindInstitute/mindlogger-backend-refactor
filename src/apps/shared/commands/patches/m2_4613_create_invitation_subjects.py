from sqlalchemy.ext.asyncio import AsyncSession

sql_subjects = """
    insert into subjects (
        id,
        applet_id,
        email,
        first_name,
        last_name,
        nickname,
        secret_user_id,
        creator_id
    )
    select
        md5(applet_id::text || (meta->>'secret_user_id'))::uuid as id,
        applet_id,
        email,
        first_name,
        last_name,
        nickname,
        meta->>'secret_user_id' as secret_user_id,
        i.invitor_id as creator_id
    from
        invitations i
    where i.role = 'respondent'
        AND i.status = 'pending';
"""

sql_invitations = """
    update invitations
    set meta = jsonb_set(
        meta,
        '{subject_id}',
        to_jsonb((md5(applet_id::text || (meta->>'secret_user_id'))::uuid))
    )
    where role = 'respondent'
        AND status = 'pending';
"""


async def main(
    session: AsyncSession,
    arbitrary_session: AsyncSession = None,
    *args,
    **kwargs,
):
    await session.execute(sql_subjects)
    await session.execute(sql_invitations)
