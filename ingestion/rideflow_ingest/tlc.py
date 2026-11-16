"""NYC TLC yellow taxi trips: CDN → S3 landing zone → ClickHouse raw.

Two idempotent steps per month:
  1. land():  stream the monthly Parquet from the TLC CDN into the lake (skipped if already there, same size)
  2. load():  replace that month's partition in raw.yellow_trips straight from S3 via ClickHouse s3()

The explicit structure + allow_missing_columns handles schema drift between years
(e.g. cbd_congestion_fee only exists from 2025; column names change case: Airport_fee/airport_fee).
"""

from __future__ import annotations

import logging
from datetime import date

import requests

from rideflow_ingest import lake
from rideflow_ingest.clickhouse import get_client

log = logging.getLogger(__name__)

CDN = "https://d37ci6vzurychx.cloudfront.net/trip-data"

# source column → raw column; types follow the TLC Parquet files
SOURCE_STRUCTURE = ", ".join([
    "VendorID Nullable(Int32)",
    "tpep_pickup_datetime DateTime64(6, 'UTC')",
    "tpep_dropoff_datetime DateTime64(6, 'UTC')",
    "passenger_count Nullable(Float64)",
    "trip_distance Nullable(Float64)",
    "RatecodeID Nullable(Float64)",
    "store_and_fwd_flag Nullable(String)",
    "PULocationID Nullable(Int32)",
    "DOLocationID Nullable(Int32)",
    "payment_type Nullable(Int64)",
    "fare_amount Nullable(Float64)",
    "extra Nullable(Float64)",
    "mta_tax Nullable(Float64)",
    "tip_amount Nullable(Float64)",
    "tolls_amount Nullable(Float64)",
    "improvement_surcharge Nullable(Float64)",
    "total_amount Nullable(Float64)",
    "congestion_surcharge Nullable(Float64)",
    "Airport_fee Nullable(Float64)",
    "cbd_congestion_fee Nullable(Float64)",
])


def file_name(month: date) -> str:
    return f"yellow_tripdata_{month:%Y-%m}.parquet"


def lake_key(month: date) -> str:
    return f"landing/tlc/yellow/year={month:%Y}/month={month:%m}/{file_name(month)}"


def is_published(month: date) -> bool:
    """TLC publishes each month ~2 months later; the CDN answers 403 until then."""
    resp = requests.head(f"{CDN}/{file_name(month)}", timeout=30)
    if resp.status_code == 200:
        return True
    if resp.status_code in (403, 404):
        return False
    resp.raise_for_status()
    return False


def land(month: date) -> str:
    key = lake_key(month)
    src = f"{CDN}/{file_name(month)}"
    with requests.get(src, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        size = int(resp.headers.get("Content-Length", 0))
        if size and lake.object_size(key) == size:
            log.info("tlc: %s already in lake (%s bytes), skip download", key, size)
            return key
        resp.raw.decode_content = True
        lake.client().upload_fileobj(resp.raw, lake.BUCKET, key)
    log.info("tlc: landed %s (%s bytes)", key, size)
    return key


def load(month: date) -> int:
    key = lake_key(month)
    access, secret = lake.credentials()
    part = int(f"{month:%Y%m}")
    ch = get_client()
    ch.command(f"ALTER TABLE raw.yellow_trips DROP PARTITION {part}")
    ch.command(
        f"""
        INSERT INTO raw.yellow_trips
        SELECT
            VendorID, tpep_pickup_datetime, tpep_dropoff_datetime, passenger_count, trip_distance,
            RatecodeID, store_and_fwd_flag, PULocationID, DOLocationID, payment_type,
            fare_amount, extra, mta_tax, tip_amount, tolls_amount, improvement_surcharge,
            total_amount, congestion_surcharge, Airport_fee, cbd_congestion_fee,
            {part}, '{key}', now64(3)
        FROM s3('{lake.url(key)}', '{access}', '{secret}', 'Parquet', $${SOURCE_STRUCTURE}$$)
        SETTINGS
            use_hive_partitioning = 0,  -- path has year=/month= but the structure is explicit
            input_format_parquet_allow_missing_columns = 1,
            input_format_parquet_case_insensitive_column_matching = 1,
            max_threads = 2,
            max_insert_threads = 1
        """
    )
    rows = ch.query(f"SELECT count() FROM raw.yellow_trips WHERE _source_month = {part}").result_rows[0][0]
    log.info("tlc: loaded %s rows into raw.yellow_trips partition %s", rows, part)
    return rows
