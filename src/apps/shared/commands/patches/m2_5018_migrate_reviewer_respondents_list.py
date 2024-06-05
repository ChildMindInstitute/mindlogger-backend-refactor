from sqlalchemy.ext.asyncio import AsyncSession

sql_invitations = """
    with respondents as (
        select
            id,
            applet_id,
            jsonb_array_elements_text(meta->'respondents') as user_id
        from
            invitations i
        where
            role = 'reviewer'
    ),
    invitation_subjects as (
        select r.id, jsonb_agg(s.id) as subjects
        from respondents r
        join subjects s
            on s.user_id::text = r.user_id and s.applet_id = r.applet_id
        group by r.id
    )
    update invitations
    set meta = jsonb_set(meta, '{subjects}', invitation_subjects.subjects)
    from invitation_subjects
    where invitations.id = invitation_subjects.id;
"""

sql_reviewers = """
    with reviewer_respondents as (
        select
            id,
            applet_id,
            jsonb_array_elements_text(meta->'respondents') as user_id
        from
            user_applet_accesses uaa
        where
            role = 'reviewer'
    ),
    reviewer_subjects as (
        select r.id, jsonb_agg(s.id) as subjects
        from reviewer_respondents r
        join subjects s
            on s.user_id::text = r.user_id and s.applet_id = r.applet_id
        group by r.id
    )
    update user_applet_accesses
    set meta = jsonb_set(meta, '{subjects}', reviewer_subjects.subjects)
    from reviewer_subjects
    where user_applet_accesses.id = reviewer_subjects.id
"""


async def main(
    session: AsyncSession,
    arbitrary_session: AsyncSession = None,
    *args,
    **kwargs,
):
    await session.execute(sql_invitations)
    await session.execute(sql_reviewers)
