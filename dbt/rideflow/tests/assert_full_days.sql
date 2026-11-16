{{ config(tags=['weather']) }}
-- Every complete local day must have 23–25 hours (23/25 on DST switch days).
-- Edge days of the loaded range are partial by construction (source is fetched
-- in UTC day boundaries, NYC is UTC-4/-5), so first and last day are excluded.
with bounds as (select min(day) as lo, max(day) as hi from {{ ref('weather_daily') }})
select day, hours_observed
from {{ ref('weather_daily') }}, bounds
where day > lo and day < hi
  and hours_observed not between 23 and 25
