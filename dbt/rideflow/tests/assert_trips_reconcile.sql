{{ config(tags=['taxi']) }}
-- Reconciliation: per source month, valid rows in staging == rows in fct_trips.
with s as (
    select _source_month, countIf(dq_status = 'ok') as expected
    from {{ ref('stg_yellow_trips') }} group by _source_month
),
f as (
    select _source_month, count() as actual
    from {{ ref('fct_trips') }} group by _source_month
)
select s._source_month, expected, f.actual
from s left join f on f._source_month = s._source_month
where expected != f.actual
