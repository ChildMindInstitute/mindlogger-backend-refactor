DO $$
DECLARE
  activity_id UUID;
BEGIN
  FOR activity_id IN (SELECT id FROM activities) LOOP
    UPDATE activities
    SET scores_and_reports = (
      SELECT jsonb_build_object('reports', jsonb_agg(item))
      FROM (
        SELECT
          jsonb_set(scores, '{type}', '"score"') AS item
        FROM jsonb_array_elements(scores_and_reports->'scores') AS scores
        WHERE activities.id = activity_id
        UNION ALL
        SELECT
          jsonb_set(sections, '{type}', '"section"') AS item
        FROM jsonb_array_elements(scores_and_reports->'sections') AS sections
        WHERE activities.id = activity_id
      ) AS item
    )
    WHERE id = activity_id;
  END LOOP;
END $$;
