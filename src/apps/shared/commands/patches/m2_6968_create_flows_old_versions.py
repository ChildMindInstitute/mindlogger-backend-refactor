from rich import print
from sqlalchemy.ext.asyncio import AsyncSession

SQL_FLOW_HISTORY_CREATE = """
    with applet_versions as (
        select
            ah.id,
            ah.id_version,
            ah.version,
            date_trunc('minute', ah.created_at) + interval '1 min' as created_at
        from applet_histories ah
        left join flow_histories fh on fh.applet_id = ah.id_version
        where 1 = 1
            and ah.id = '{applet_id}'
            and format(
                '%s.%s.%s',
                lpad(split_part(ah."version", '.', 1), 2, '0'),
                lpad(split_part(ah."version", '.', 2), 2, '0'),
                lpad(split_part(ah."version", '.', 3), 2, '0')
            ) >= '{from_version_padded}'
            and fh.id is null
    ),
    last_flow_data as (
        select f.*
        from flows f 
        where f.applet_id = '{applet_id}'
    )
    insert into flow_histories
    select
        av.created_at,
        av.created_at as updated_at,
        lf.is_deleted,
        lf."name",
        lf.description,
        lf.is_single_report,
        lf.hide_badge,
        lf."order",
        format('%s_%s', lf.id::text, av.version) as id_version,
        av.id_version as applet_id,
        lf.id,
        lf.is_hidden,
        lf.report_included_activity_name,
        lf.report_included_item_name,
        lf.extra_fields
    from last_flow_data lf
    cross join applet_versions av;
"""

SQL_FLOW_ITEM_HISTORY_CREATE = """
    with applet_versions as (
        select
            ah.id,
            ah.id_version,
            ah.version,
            date_trunc('minute', ah.created_at) + interval '1 min' as created_at
        from applet_histories ah
        left join flow_histories fh on fh.applet_id = ah.id_version
            and exists (select 1 from flow_item_histories fih where fih.activity_flow_id = fh.id_version)
        where 1 = 1
            and ah.id = '{applet_id}'
            and format(
                '%s.%s.%s',
                lpad(split_part(ah."version", '.', 1), 2, '0'),
                lpad(split_part(ah."version", '.', 2), 2, '0'),
                lpad(split_part(ah."version", '.', 3), 2, '0')
            ) >= '{from_version_padded}'
            and fh.id is null
    ),
    last_flow_item_data as (
        select fi.*
        from flows f 
        join flow_items fi on fi.activity_flow_id = f.id
        where f.applet_id = '{applet_id}'
    )
    insert into flow_item_histories
    select 
        av.created_at,
        av.created_at as updated_at,
        lfi.is_deleted,
        lfi."order",
        format('%s_%s', lfi.id::text, av.version) as id_version,
        format('%s_%s', lfi.activity_flow_id::text, av.version) as activity_flow_id,
        format('%s_%s', lfi.activity_id::text, av.version) as activity_id,
        lfi.id
    from last_flow_item_data lfi
    cross join applet_versions av;
"""

applet_versions = (
    ("62b21984-b90b-7f2b-a9e1-c51a00000000", "10.00.00"),
    ("7bb7b30e-0d8a-4b13-bc1c-6a733ccc689a", "02.00.00"),
)


async def main(session: AsyncSession, *args, **kwargs):
    for applet_id, version_padded in applet_versions:
        sql = SQL_FLOW_HISTORY_CREATE.format(applet_id=applet_id, from_version_padded=version_padded)
        print("Execute:")
        print(sql)
        await session.execute(sql)
        print("Done")
        print("Execute:")
        print(sql)
        sql = SQL_FLOW_ITEM_HISTORY_CREATE.format(applet_id=applet_id, from_version_padded=version_padded)
        print("Done")
        await session.execute(sql)
