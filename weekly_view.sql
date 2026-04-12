CREATE OR REPLACE VIEW prod.weekly AS
WITH bounds AS (
  SELECT
    (NOW() AT TIME ZONE 'America/Toronto')::date AS local_today,
    (
      (NOW() AT TIME ZONE 'America/Toronto')::date
      - ((EXTRACT(DOW FROM (NOW() AT TIME ZONE 'America/Toronto')::date)::int + 1) % 7)
    )::date AS last_sat
)
SELECT
  u.username,

  -- Week 1: last Sat .. today (inclusive)
  COALESCE(
    NULLIF(
      COUNT(*) FILTER (
        WHERE w.local_date >= b.last_sat
          AND w.local_date <= b.local_today
      ), 0
    )::text, ''
  ) AS week1,

  -- Week 2: previous Sat .. Fri
  COALESCE(
    NULLIF(
      COUNT(*) FILTER (
        WHERE w.local_date >= b.last_sat - INTERVAL '7 days'
          AND w.local_date <  b.last_sat
      ), 0
    )::text, ''
  ) AS week2,

  -- Week 3: two weeks ago Sat .. Fri
  COALESCE(
    NULLIF(
      COUNT(*) FILTER (
        WHERE w.local_date >= b.last_sat - INTERVAL '14 days'
          AND w.local_date <  b.last_sat - INTERVAL '7 days'
      ), 0
    )::text, ''
  ) AS week3,

  -- Week 4: three weeks ago Sat .. Fri
  COALESCE(
    NULLIF(
      COUNT(*) FILTER (
        WHERE w.local_date >= b.last_sat - INTERVAL '21 days'
          AND w.local_date <  b.last_sat - INTERVAL '14 days'
      ), 0
    )::text, ''
  ) AS week4

FROM prod.user_table u
CROSS JOIN bounds b
LEFT JOIN (
  SELECT
    username,
    (last_updated AT TIME ZONE 'America/Toronto')::date AS local_date
  FROM prod.user_works
  WHERE work_status = 'Done'
) AS w
  ON w.username = u.username
WHERE u.isactive = true
GROUP BY u.username, b.local_today, b.last_sat
ORDER BY u.username;
