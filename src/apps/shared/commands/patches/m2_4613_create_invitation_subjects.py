from sqlalchemy.ext.asyncio import AsyncSession

sql_subjects_pending = """
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

sql_invitations_pending = """
    update invitations
    set meta = jsonb_set(
        meta,
        '{subject_id}',
        to_jsonb((md5(applet_id::text || (meta->>'secret_user_id'))::uuid))
    )
    where role = 'respondent'
        AND status = 'pending';
"""

sql_invitations_accepted = """
    update invitations
    set meta = jsonb_set(
        coalesce(meta, '{}'::jsonb),
        '{subject_id}',
        to_jsonb((md5(applet_id::text || user_id::text)::uuid))
    )
    where role = 'respondent'
        AND status = 'approved';
"""


async def main(
    session: AsyncSession,
    arbitrary_session: AsyncSession = None,
    *args,
    **kwargs,
):
    await session.execute(sql_invitations_accepted)
    await session.execute(sql_subjects_pending)
    await session.execute(sql_invitations_pending)
