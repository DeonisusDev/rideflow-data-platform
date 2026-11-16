-- NYC TLC yellow taxi trips, loaded month-by-month from the S3 landing zone.
-- Source timestamps are *naive local NYC time*; they are kept as-is here
-- (stored in a UTC-typed column = wall clock) and converted to real instants in dbt staging.
-- Partitioned by the source file month, so a re-run replaces exactly one partition.
CREATE TABLE IF NOT EXISTS raw.yellow_trips
(
    vendor_id             Nullable(Int32),
    pickup_local          DateTime64(6, 'UTC'),
    dropoff_local         DateTime64(6, 'UTC'),
    passenger_count       Nullable(Float64),
    trip_distance         Nullable(Float64),
    ratecode_id           Nullable(Float64),
    store_and_fwd_flag    Nullable(String),
    pu_location_id        Nullable(Int32),
    do_location_id        Nullable(Int32),
    payment_type          Nullable(Int64),
    fare_amount           Nullable(Float64),
    extra                 Nullable(Float64),
    mta_tax               Nullable(Float64),
    tip_amount            Nullable(Float64),
    tolls_amount          Nullable(Float64),
    improvement_surcharge Nullable(Float64),
    total_amount          Nullable(Float64),
    congestion_surcharge  Nullable(Float64),
    airport_fee           Nullable(Float64),
    cbd_congestion_fee    Nullable(Float64),   -- appears in source from 2025-01 (schema drift)
    _source_month         UInt32,              -- YYYYMM of the source file
    _source_file          LowCardinality(String),
    _loaded_at            DateTime64(3, 'UTC')
)
ENGINE = MergeTree
PARTITION BY _source_month
ORDER BY (_source_month, pickup_local);
