from sqlalchemy.ext.asyncio import AsyncSession

UPDATE_APPLET_SQL = """
    UPDATE applets
    SET
        "display_name" = regexp_replace("display_name", '&amp;', '&', 'g'),
        "about" = regexp_replace(about::text, '&amp;', '&', 'g')::jsonb,
        "description" = regexp_replace(description::text, '&amp;', '&', 'g')::jsonb
    WHERE
        "display_name" LIKE '%&amp;%'
        OR (about->>'en' LIKE '%&amp;%' OR about->>'fr' LIKE '%&amp;%')
        OR (description->>'en' LIKE '%&amp;%' OR description->>'fr' LIKE '%&amp;%');
"""

UPDATE_APPLET_HISTORY_SQL = """
    UPDATE applet_histories
    SET
        "display_name" = regexp_replace("display_name", '&amp;', '&', 'g'),
        "about" = regexp_replace(about::text, '&amp;', '&', 'g')::jsonb,
        "description" = regexp_replace(description::text, '&amp;', '&', 'g')::jsonb
    WHERE
        "display_name" LIKE '%&amp;%'
        OR (about->>'en' LIKE '%&amp;%' OR about->>'fr' LIKE '%&amp;%')
        OR (description->>'en' LIKE '%&amp;%' OR description->>'fr' LIKE '%&amp;%');
"""

UPDATE_ACTIVITY_SQL = """
    UPDATE activities
    SET 
        "name" = regexp_replace("name", '&amp;', '&', 'g'),
        "description" = regexp_replace(description::text, '&amp;', '&', 'g')::jsonb
    WHERE "name" LIKE '%&amp;%' OR (description->>'en' LIKE '%&amp;%' OR description->>'fr' LIKE '%&amp;%');
"""

UPDATE_ACTIVITY_HISTORY_SQL = """
    UPDATE activity_histories
    SET 
        "name" = regexp_replace("name", '&amp;', '&', 'g'),
        "description" = regexp_replace(description::text, '&amp;', '&', 'g')::jsonb
    WHERE "name" LIKE '%&amp;%' OR (description->>'en' LIKE '%&amp;%' OR description->>'fr' LIKE '%&amp;%');
"""


UPDATE_ACTIVITY_SCORES_AND_REPORTS_SQL = """
    UPDATE activities
    SET scores_and_reports = regexp_replace(scores_and_reports::text, '&amp;', '&', 'g')::jsonb
    WHERE EXISTS (
        SELECT 1
        FROM jsonb_array_elements(scores_and_reports->'reports') AS report
        WHERE report->>'message' LIKE '%&amp;%'
    );
"""

UPDATE_ACTIVITY_HISTORY_SCORES_AND_REPORTS_SQL = """
    UPDATE activity_histories
    SET scores_and_reports = regexp_replace(scores_and_reports::text, '&amp;', '&', 'g')::jsonb
    WHERE EXISTS (
        SELECT 1
        FROM jsonb_array_elements(scores_and_reports->'reports') AS report
        WHERE report->>'message' LIKE '%&amp;%'
    );
"""

UPDATE_ACTIVITY_ITEM_SQL = """
    UPDATE activity_items
    SET 
        "name" = regexp_replace("name", '&amp;', '&', 'g'),
        "question" = regexp_replace(question::text, '&amp;', '&', 'g')::jsonb
    WHERE "name" LIKE '%&amp;%' OR (question->>'en' LIKE '%&amp;%' OR question->>'fr' LIKE '%&amp;%');
"""
UPDATE_ACTIVITY_ITEM_HISTORY_SQL = """
    UPDATE activity_item_histories
    SET 
        "name" = regexp_replace("name", '&amp;', '&', 'g'),
        "question" = regexp_replace(question::text, '&amp;', '&', 'g')::jsonb
    WHERE "name" LIKE '%&amp;%' OR (question->>'en' LIKE '%&amp;%' OR question->>'fr' LIKE '%&amp;%');
"""

UPDATE_FLOW_SQL = """
    UPDATE flows
    SET 
        "name" = regexp_replace("name", '&amp;', '&', 'g'),
        "description" = regexp_replace(description::text, '&amp;', '&', 'g')::jsonb
    WHERE "name" LIKE '%&amp;%' OR (description->>'en' LIKE '%&amp;%' OR description->>'fr' LIKE '%&amp;%');
"""

UPDATE_FLOW_HISTORY__SQL = """
    UPDATE flow_histories
    SET 
        "name" = regexp_replace("name", '&amp;', '&', 'g'),
        "description" = regexp_replace(description::text, '&amp;', '&', 'g')::jsonb
    WHERE "name" LIKE '%&amp;%' OR (description->>'en' LIKE '%&amp;%' OR description->>'fr' LIKE '%&amp;%');
"""

QUERIES = [
    UPDATE_APPLET_SQL,
    UPDATE_APPLET_HISTORY_SQL,
    UPDATE_ACTIVITY_SQL,
    UPDATE_ACTIVITY_HISTORY_SQL,
    UPDATE_ACTIVITY_SCORES_AND_REPORTS_SQL,
    UPDATE_ACTIVITY_HISTORY_SCORES_AND_REPORTS_SQL,
    UPDATE_ACTIVITY_ITEM_SQL,
    UPDATE_ACTIVITY_ITEM_HISTORY_SQL,
    UPDATE_FLOW_SQL,
    UPDATE_FLOW_HISTORY__SQL,
]


async def main(session: AsyncSession, *args, **kwargs):
    try:
        for sql in QUERIES:
            await session.execute(sql)
        await session.commit()
    except Exception as ex:
        await session.rollback()
        raise ex
