-- Starter analysis over the long-format observation table. Every wss repo
-- emits the same schema:
--   observations(series_id, entity_id, observed_at, captured_at, metric,
--                value, unit, source_id, raw_ref, parser_version)
-- Here entity_id is a floodAreaID (e.g. 053WAF113LWA).

-- 1. WHAT IS FLOODING RIGHT NOW, worst first.
WITH latest AS (SELECT MAX(observed_at) AS t FROM observations)
SELECT o.entity_id,
       MAX(CASE WHEN metric = 'description'    THEN value END) AS area,
       MAX(CASE WHEN metric = 'county'         THEN value END) AS county,
       MAX(CASE WHEN metric = 'severity'       THEN value END) AS severity,
       MAX(CASE WHEN metric = 'severity_level' THEN CAST(value AS INTEGER) END) AS lvl
FROM observations o, latest
WHERE o.observed_at = latest.t
GROUP BY o.entity_id
ORDER BY lvl ASC, county;

-- 2. THE DELETION WINDOW -- this repo's central question.
-- How many consecutive hourly captures does a warning sit at severity 4
-- ("no longer in force") before the publisher removes the row entirely?
-- Nothing outside an hourly capture can answer this.
SELECT entity_id,
       MAX(CASE WHEN metric='warning_id' THEN value END) AS warning_id,
       COUNT(*)            AS hours_at_level_4,
       MIN(observed_at)    AS stood_down_at,
       MAX(observed_at)    AS last_seen_before_deletion
FROM observations
WHERE metric = 'severity_level' AND CAST(value AS INTEGER) = 4
GROUP BY entity_id
ORDER BY hours_at_level_4 DESC;

-- 3. AREAS THAT FLOOD REPEATEDLY.
-- Break on warning_id, never on presence: the same floodAreaID floods many
-- times, and a changed warning number is a NEW event, not a continuing one.
SELECT entity_id,
       COUNT(DISTINCT value) AS separate_events,
       MIN(observed_at)      AS first_event,
       MAX(observed_at)      AS latest_event
FROM observations
WHERE metric = 'warning_id'
GROUP BY entity_id
HAVING separate_events > 1
ORDER BY separate_events DESC;

-- 4. ESCALATION PATH of a single event: did an alert become a warning?
SELECT observed_at, CAST(value AS INTEGER) AS severity_level
FROM observations
WHERE metric = 'severity_level' AND entity_id = '053WAF113LWA'
ORDER BY observed_at;

-- 5. A ZERO THAT IS REAL. Most hours, no part of England is flooding and the
-- register is empty. An hour with a capture but no observations is a measured
-- national all-clear, NOT a failed fetch -- the gates in the registry are what
-- separate those. Count them before quoting any per-hour rate.
SELECT COUNT(DISTINCT observed_at) AS hours_with_at_least_one_warning
FROM observations;
