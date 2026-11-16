{{ config(
    tags=['taxi'],
    materialized='incremental',
    incremental_strategy='insert_overwrite',
    partition_by='source_month',
    order_by='(source_month, dq_status)',
    engine='MergeTree()'
) }}
-- Rows per source month and DQ status. Incremental like fct_trips: only months (re)loaded
-- into raw since the last run are recomputed; their partitions are replaced.
select
    _source_month                                                            as source_month,
    dq_status,
    count()                                                                  as rows,
    round(100 * count() / sum(count()) over (partition by _source_month), 3) as pct,
    max(_loaded_at)                                                          as last_loaded_at  -- not _loaded_at: the alias would shadow the column in WHERE
from {{ ref('stg_yellow_trips') }}
{% if is_incremental() %}
where _loaded_at > (select max(last_loaded_at) from {{ this }})
{% endif %}
group by _source_month, dq_status
